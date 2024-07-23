# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import afni

from ...interfaces.fslnumpy.tempfilt import TemporalFilter
from ...interfaces.image_maths.add_means import AddMeans
from ...interfaces.utility.afni import FromAFNI, ToAFNI
from ..memory import MemoryCalculator


def _calc_sigma(
    lp_width: float | None = None,
    hp_width: float | None = None,
    repetition_time: float | None = None,
):
    lp_sigma = None
    hp_sigma = None

    if lp_width is not None or hp_width is not None:
        if not isinstance(repetition_time, float):
            raise ValueError(f'Invalid repetition time "{repetition_time}" ({type(repetition_time)})')
        if lp_width is not None:
            lp_sigma = lp_width / (2.0 * repetition_time)
        if hp_width is not None:
            hp_sigma = hp_width / (2.0 * repetition_time)

    return lp_sigma, hp_sigma


def _out_file_name(in_file) -> str:
    from halfpipe.utils.path import split_ext

    stem, ext = split_ext(in_file)
    return f"{stem}_tproject{ext}"


def _bandpass_arg(low, high) -> str:
    low, high = float(low), float(high)

    # constants taken from https://github.com/afni/afni/blob/master/src/3dTproject.c#L1312-L1313
    if low < 0 and high < 0:
        return ""  # only remove selected confounds
    elif high < 0:
        return f"-stopband 0 {low - 0.0001:f}"
    elif low < 0:
        return f"-stopband {high + 0.0001:f} 999999.9"
    else:
        return f"-passband {low:f} {high:f}"


BandpassFilterTuple = tuple[str, float | None, float | None]


def init_bandpass_filter_wf(
    bandpass_filter: BandpassFilterTuple,
    name: str | None = None,
    suffix: str | None = None,
    memcalc: MemoryCalculator | None = None,
) -> pe.Workflow:
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    type, low, high = bandpass_filter

    if name is None:
        name = f"{type}_bandpass_filter"
        if low is not None:
            name = f"{name}_low_{int(low * 1000):d}"
        if high is not None:
            name = f"{name}_high_{int(high * 1000):d}"
        name = f"{name}_wf"
    if suffix is not None:
        name = f"{name}_{suffix}"

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "low", "high", "vals", "repetition_time"]),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "vals"]),
        name="outputnode",
    )

    workflow.connect(inputnode, "mask", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    if low is not None:
        inputnode.inputs.low = low
    else:
        inputnode.inputs.low = -1.0

    if high is not None:
        inputnode.inputs.high = high
    else:
        inputnode.inputs.high = -1.0

    add_means = pe.MapNode(
        AddMeans(),
        iterfield=["in_file", "mean_file"],
        name="add_means",
        mem_gb=memcalc.series_std_gb * 2,
    )
    workflow.connect(inputnode, "files", add_means, "mean_file")

    workflow.connect(add_means, "out_file", outputnode, "files")

    if type == "gaussian":
        calcsigma = pe.Node(
            niu.Function(
                input_names=["lp_width", "hp_width", "repetition_time"],
                output_names=["lp_sigma", "hp_sigma"],  # type: ignore
                function=_calc_sigma,
            ),
            name="calcsigma",
        )
        workflow.connect(inputnode, "low", calcsigma, "lp_width")
        workflow.connect(inputnode, "high", calcsigma, "hp_width")
        workflow.connect(inputnode, "repetition_time", calcsigma, "repetition_time")
        temporalfilter = pe.MapNode(
            TemporalFilter(),
            iterfield="in_file",
            name="temporalfilter",
            mem_gb=memcalc.series_std_gb * 2,
        )
        workflow.connect(calcsigma, "lp_sigma", temporalfilter, "lowpass_sigma")
        workflow.connect(calcsigma, "hp_sigma", temporalfilter, "highpass_sigma")
        workflow.connect(inputnode, "files", temporalfilter, "in_file")
        workflow.connect(inputnode, "mask", temporalfilter, "mask")

        workflow.connect(temporalfilter, "out_file", add_means, "in_file")
    elif type == "frequency_based":
        toafni = pe.MapNode(ToAFNI(), iterfield="in_file", name="toafni")
        workflow.connect(inputnode, "files", toafni, "in_file")

        makeoutfname = pe.MapNode(
            niu.Function(
                input_names=["in_file"],
                output_names="out_file",
                function=_out_file_name,
            ),
            iterfield="in_file",
            name="tprojectoutfilename",
        )
        workflow.connect(toafni, "out_file", makeoutfname, "in_file")

        bandpass_arg = pe.Node(
            niu.Function(
                input_names=["low", "high"],
                output_names="out",
                function=_bandpass_arg,
            ),
            name="bandpass_arg",
        )
        workflow.connect(inputnode, "low", bandpass_arg, "low")
        workflow.connect(inputnode, "high", bandpass_arg, "high")

        tproject = pe.MapNode(
            afni.TProject(polort=1),
            iterfield=["in_file", "out_file"],
            name="tproject",
            mem_gb=memcalc.series_std_gb * 2,
        )
        workflow.connect(toafni, "out_file", tproject, "in_file")
        workflow.connect(bandpass_arg, "out", tproject, "args")
        workflow.connect(inputnode, "repetition_time", tproject, "TR")
        workflow.connect(makeoutfname, "out_file", tproject, "out_file")

        fromafni = pe.MapNode(FromAFNI(), iterfield=["in_file", "metadata"], name="fromafni")
        workflow.connect(toafni, "metadata", fromafni, "metadata")
        workflow.connect(tproject, "out_file", fromafni, "in_file")

        workflow.connect(fromafni, "out_file", add_means, "in_file")
    else:
        raise ValueError(f"Unknown bandpass_filter type '{type}'")

    return workflow
