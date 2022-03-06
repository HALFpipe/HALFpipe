# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from fmriprep import config
from nipype.algorithms import confounds as nac
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from niworkflows.interfaces.utility import KeySelect
from niworkflows.utils.spaces import SpatialReferences

from ...interfaces.imagemaths.resample import Resample
from ...interfaces.report.imageplot import PlotEpi, PlotRegistration
from ...interfaces.report.vals import CalcMean, UpdateVals
from ...interfaces.resultdict.datasink import ResultdictDatasink
from ...interfaces.resultdict.make import MakeResultdicts
from ..constants import constants
from ..memory import MemoryCalculator


def _calc_scan_start(skip_vols: int, repetition_time: float) -> float:
    return skip_vols * repetition_time


def init_func_report_wf(
    workdir=None, name="func_report_wf", memcalc=MemoryCalculator.default()
):
    """ """
    workflow = pe.Workflow(name=name)

    #
    fmriprepreports = ["bold_conf", "reg", "bold_rois", "compcor", "conf_corr", "sdc"]
    fmriprepreportdatasinks = [f"ds_report_{fr}" for fr in fmriprepreports]

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_std",
                "bold_std_ref",
                "bold_mask_std",
                "std_dseg",
                "spatial_reference",
                "movpar_file",
                "confounds_file",
                "method",
                "fallback",
                *fmriprepreportdatasinks,
                "fd_thres",
                "repetition_time",
                "skip_vols",
                "tags",
            ]
        ),
        name="inputnode",
    )

    select_std = pe.Node(
        KeySelect(fields=["bold_std", "bold_std_ref", "bold_mask_std", "std_dseg"]),
        name="select_std",
        run_without_submitting=True,
        nohash=True,
    )
    select_std.inputs.key = f"{constants.reference_space}_res-{constants.reference_res}"
    workflow.connect(inputnode, "bold_std", select_std, "bold_std")
    workflow.connect(inputnode, "bold_std_ref", select_std, "bold_std_ref")
    workflow.connect(inputnode, "bold_mask_std", select_std, "bold_mask_std")
    workflow.connect(inputnode, "std_dseg", select_std, "std_dseg")
    workflow.connect(inputnode, "spatial_reference", select_std, "keys")

    #
    outputnode = pe.Node(niu.IdentityInterface(fields=["vals"]), name="outputnode")

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(
            reportkeys=["epi_norm_rpt", "tsnr_rpt", "carpetplot", *fmriprepreports],
            valkeys=[
                "dummy_scans",
                "sdc_method",
                "scan_start",
                "fallback_registration",
            ],
        ),
        name="make_resultdicts",
    )
    workflow.connect(inputnode, "skip_vols", make_resultdicts, "dummy_scans")
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "method", make_resultdicts, "sdc_method")
    workflow.connect(inputnode, "fallback", make_resultdicts, "fallback_registration")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    for fr, frd in zip(fmriprepreports, fmriprepreportdatasinks):
        workflow.connect(inputnode, frd, make_resultdicts, fr)

    # EPI -> mni
    spaces = config.workflow.spaces
    assert isinstance(spaces, SpatialReferences)
    epi_norm_rpt = pe.Node(
        PlotRegistration(template=spaces.get_spaces()[0]),
        name="epi_norm_rpt",
        mem_gb=0.1,
    )
    workflow.connect(select_std, "bold_std_ref", epi_norm_rpt, "in_file")
    workflow.connect(select_std, "bold_mask_std", epi_norm_rpt, "mask_file")
    workflow.connect(epi_norm_rpt, "out_report", make_resultdicts, "epi_norm_rpt")

    # plot the tsnr image
    tsnr = pe.Node(nac.TSNR(), name="compute_tsnr", mem_gb=memcalc.series_std_gb * 2.5)
    workflow.connect(select_std, "bold_std", tsnr, "in_file")

    tsnr_rpt = pe.Node(PlotEpi(), name="tsnr_rpt", mem_gb=memcalc.min_gb)
    workflow.connect(tsnr, "tsnr_file", tsnr_rpt, "in_file")
    workflow.connect(select_std, "bold_mask_std", tsnr_rpt, "mask_file")
    workflow.connect(tsnr_rpt, "out_report", make_resultdicts, "tsnr_rpt")

    #
    reference_dict = dict(
        reference_space=constants.reference_space, reference_res=constants.reference_res
    )
    reference_dict["input_space"] = reference_dict["reference_space"]
    resample = pe.Node(
        Resample(interpolation="MultiLabel", **reference_dict),
        name="resample",
        mem_gb=2 * memcalc.volume_std_gb,
    )
    workflow.connect(select_std, "std_dseg", resample, "input_image")

    # based on https://github.com/bids-standard/bids-specification/issues/836#issue-954042717
    calc_scan_start = pe.Node(
        niu.Function(
            input_names=["skip_vols", "repetition_time"],
            output_names="scan_start",
            function=_calc_scan_start,
        ),
        name="calc_scan_start",
    )
    workflow.connect(inputnode, "skip_vols", calc_scan_start, "skip_vols")
    workflow.connect(inputnode, "repetition_time", calc_scan_start, "repetition_time")

    workflow.connect(calc_scan_start, "scan_start", make_resultdicts, "scan_start")

    # vals
    confvals = pe.Node(UpdateVals(), name="confvals", mem_gb=2 * memcalc.volume_std_gb)
    workflow.connect(inputnode, "fd_thres", confvals, "fd_thres")
    workflow.connect(inputnode, "confounds_file", confvals, "confounds_file")

    calcmean = pe.Node(
        CalcMean(key="mean_gm_tsnr"),
        name="calcmean",
        mem_gb=2 * memcalc.volume_std_gb,
    )
    workflow.connect(confvals, "vals", calcmean, "vals")  # base dict to update
    workflow.connect(tsnr, "tsnr_file", calcmean, "in_file")
    workflow.connect(resample, "output_image", calcmean, "dseg")

    workflow.connect(calcmean, "vals", make_resultdicts, "vals")
    workflow.connect(make_resultdicts, "vals", outputnode, "vals")

    return workflow
