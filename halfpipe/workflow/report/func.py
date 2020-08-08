# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.algorithms import confounds as nac

from fmriprep import config

from ...interface import (
    Exec,
    PlotRegistration,
    PlotEpi,
    Vals,
    CalcMean,
    Resample,
    MakeResultdicts,
    ResultdictDatasink
)

from ..constants import constants
from ..memory import MemoryCalculator


def init_func_report_wf(workdir=None, fd_thres=None, name="func_report_wf", memcalc=MemoryCalculator()):
    """

    """
    workflow = pe.Workflow(name=name)

    #
    fmriprepreports = ["bold_conf", "reg", "bold_rois", "compcor", "conf_corr", "sdc"]
    fmriprepreportdatasinks = [f"ds_report_{fr}" for fr in fmriprepreports]
    strfields = [
        "bold_std",
        "bold_std_ref",
        "bold_mask_std",
        "movpar_file",
        "skip_vols",
        "confounds",
        "std_dseg",
        *fmriprepreportdatasinks,
    ]
    inputnode = pe.Node(
        Exec(
            fieldtpls=[
                ("tags", None),
                *[(field, "firststr") for field in strfields],
                ("fd_thres", None)
            ]
        ),
        name="inputnode",
        run_without_submitting=True
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["vals"]), name="outputnode")

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(
            reportkeys=["epi_norm_rpt", "tsnr_rpt", "carpetplot", *fmriprepreports]
        ),
        name="make_resultdicts",
        run_without_submitting=True
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "skip_vols", make_resultdicts, "dummy")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    for fr, frd in zip(fmriprepreports, fmriprepreportdatasinks):
        workflow.connect(inputnode, frd, make_resultdicts, fr)

    # EPI -> mni
    epi_norm_rpt = pe.Node(
        PlotRegistration(template=config.workflow.spaces.get_spaces()[0]),
        name="epi_norm_rpt",
        mem_gb=0.1,
    )
    workflow.connect(inputnode, "bold_std_ref", epi_norm_rpt, "in_file")
    workflow.connect(inputnode, "bold_mask_std", epi_norm_rpt, "mask_file")
    workflow.connect(epi_norm_rpt, "out_report", make_resultdicts, "epi_norm_rpt")

    # plot the tsnr image
    tsnr = pe.Node(nac.TSNR(), name="compute_tsnr", mem_gb=memcalc.series_std_gb)
    workflow.connect(inputnode, "bold_std", tsnr, "in_file")

    tsnr_rpt = pe.Node(PlotEpi(), name="tsnr_rpt", mem_gb=memcalc.min_gb)
    workflow.connect(tsnr, "tsnr_file", tsnr_rpt, "in_file")
    workflow.connect(inputnode, "bold_mask_std", tsnr_rpt, "mask_file")
    workflow.connect(tsnr_rpt, "out_report", make_resultdicts, "tsnr_rpt")

    #
    reference_dict = dict(reference_space=constants.reference_space, reference_res=constants.reference_res)
    reference_dict["input_space"] = reference_dict["reference_space"]
    resample = pe.Node(
        Resample(interpolation="MultiLabel", **reference_dict),
        name="resample",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "std_dseg", resample, "input_image")

    # vals
    confvals = pe.Node(
        Vals(), name="vals", mem_gb=memcalc.series_std_gb, run_without_submitting=True
    )
    workflow.connect(inputnode, "fd_thres", confvals, "fd_thres")
    workflow.connect(inputnode, "confounds", confvals, "confounds")

    calcmean = pe.Node(
        CalcMean(key="mean_gm_tsnr"), name="calcmean", mem_gb=memcalc.series_std_gb
    )
    workflow.connect(confvals, "vals", calcmean, "vals")  # base dict to update
    workflow.connect(tsnr, "tsnr_file", calcmean, "in_file")
    workflow.connect(resample, "output_image", calcmean, "dseg")

    workflow.connect(calcmean, "vals", make_resultdicts, "vals")
    workflow.connect(calcmean, "vals", outputnode, "vals")

    return workflow
