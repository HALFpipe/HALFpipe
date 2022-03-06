# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import afni

from ...interfaces.fslnumpy.tempfilt import TemporalFilter
from ...interfaces.imagemaths.addmeans import AddMeans
from ...interfaces.utility.afni import FromAFNI, ToAFNI
from ..memory import MemoryCalculator


def _calc_sigma(
    lp_width: float | None = None,
    hp_width: float | None = None,
    repetition_time: float | None = None,
):
    lp_sigma = None
    if lp_width is not None:
        assert isinstance(repetition_time, float)
        lp_sigma = lp_width / (2.0 * repetition_time)
    hp_sigma = None
    if hp_width is not None:
        assert isinstance(repetition_time, float)
        hp_sigma = hp_width / (2.0 * repetition_time)
    return lp_sigma, hp_sigma


def _out_file_name(in_file):
    from halfpipe.utils.path import split_ext

    stem, ext = split_ext(in_file)
    return f"{stem}_tproject{ext}"


def _bandpass_arg(low, high):
    return (float(low), float(high))


def init_bandpass_filter_wf(
    bandpass_filter: tuple[str, float, float],
    name: str | None = None,
    suffix: str | None = None,
    memcalc: MemoryCalculator = MemoryCalculator.default(),
):
    type, low, high = bandpass_filter

    if name is None:
        name = f"{type}_bandpass_filter"
        if low is not None:
            name = f"{name}_{int(low * 1000):d}"
        if low is not None:
            name = f"{name}_{int(high * 1000):d}"
        name = f"{name}_wf"
    if suffix is not None:
        name = f"{name}_{suffix}"

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["files", "mask", "low", "high", "vals", "repetition_time"]
        ),
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

    addmeans = pe.MapNode(
        AddMeans(),
        iterfield=["in_file", "mean_file"],
        name="addmeans",
        mem_gb=memcalc.series_std_gb * 2,
    )
    workflow.connect(inputnode, "files", addmeans, "mean_file")

    workflow.connect(addmeans, "out_file", outputnode, "files")

    if type == "gaussian":
        calcsigma = pe.Node(
            niu.Function(
                input_names=["lp_width", "hp_width", "repetition_time"],
                output_names=["lp_sigma", "hp_sigma"],
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

        workflow.connect(temporalfilter, "out_file", addmeans, "in_file")
    elif type == "frequency_based":
        toafni = pe.MapNode(ToAFNI(), iterfield="in_file", name="toafni")
        workflow.connect(inputnode, "files", toafni, "in_file")

        makeoutfname = pe.MapNode(
            niu.Function(
                input_names=["in_file"],
                output_names=["out_file"],
                function=_out_file_name,
            ),
            iterfield="in_file",
            name="tprojectoutfilename",
        )
        workflow.connect(toafni, "out_file", makeoutfname, "in_file")

        bandpassarg = pe.Node(
            niu.Function(
                input_names=["low", "high"],
                output_names=["out"],
                function=_bandpass_arg,
            ),
            name="bandpassarg",
        )  # cannot use merge here as we need a tuple
        workflow.connect(inputnode, "low", bandpassarg, "low")
        workflow.connect(inputnode, "high", bandpassarg, "high")

        tproject = pe.MapNode(
            afni.TProject(polort=1),
            iterfield=["in_file", "out_file"],
            name="tproject",
            mem_gb=memcalc.series_std_gb * 2,
        )
        workflow.connect(toafni, "out_file", tproject, "in_file")
        workflow.connect(bandpassarg, "out", tproject, "bandpass")
        workflow.connect(inputnode, "repetition_time", tproject, "TR")
        workflow.connect(makeoutfname, "out_file", tproject, "out_file")

        fromafni = pe.MapNode(
            FromAFNI(), iterfield=["in_file", "metadata"], name="fromafni"
        )
        workflow.connect(toafni, "metadata", fromafni, "metadata")
        workflow.connect(tproject, "out_file", fromafni, "in_file")

        workflow.connect(fromafni, "out_file", addmeans, "in_file")
    else:
        raise ValueError(f"Unknown bandpass_filter type '{type}'")

    return workflow
