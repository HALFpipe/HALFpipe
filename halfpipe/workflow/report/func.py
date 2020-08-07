# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu, afni
from nipype.algorithms import confounds as nac

from niworkflows.interfaces.plotting import FMRISummary
from mriqc.workflows.functional import spikes_mask
from mriqc.interfaces import Spikes
from fmriprep import config
from mriqc import config as mriqcconfig
from templateflow.api import get as get_template

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


def init_func_report_wf(workdir=None, name="func_report_wf", memcalc=MemoryCalculator()):
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
        *fmriprepreportdatasinks,
    ]
    inputnode = pe.Node(
        Exec(
            fieldtpls=[
                ("tags", None),
                *[(field, "firststr") for field in strfields],
                ("std_dseg", "ravel"),
            ]
        ),
        name="inputnode",
    )

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(
            reportkeys=["epi_norm_rpt", "tsnr_rpt", "carpetplot", *fmriprepreports],
            valkeys=["mean_gm_tsnr", "fd_mean", "fd_perc", "dummy"],
        ),
        name="make_resultdicts",
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

    # carpetplot
    add_carpetplot(workflow, memcalc)

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
    vals = pe.Node(
        Vals(), name="vals", mem_gb=memcalc.series_std_gb
    )
    workflow.connect(inputnode, "confounds", vals, "confounds")

    workflow.connect(vals, "fd_mean", make_resultdicts, "fd_mean")
    workflow.connect(vals, "fd_perc", make_resultdicts, "fd_perc")

    calcmean = pe.Node(
        CalcMean(), name="calcmean", mem_gb=memcalc.series_std_gb
    )
    workflow.connect(tsnr, "tsnr_file", calcmean, "in_file")
    workflow.connect(resample, "output_image", calcmean, "dseg")

    workflow.connect(calcmean, "mean", make_resultdicts, "mean_gm_tsnr")

    return workflow


def add_carpetplot(workflow, memcalc):
    inputnode = workflow.get_node("inputnode")
    make_resultdicts = workflow.get_node("make_resultdicts")

    fdisp = pe.Node(
        nac.FramewiseDisplacement(parameter_source="SPM"),
        name="fdisp",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "movpar_file", fdisp, "in_file")

    computedvars = pe.Node(
        nac.ComputeDVARS(save_plot=False, save_all=True),
        name="computedvars",
        mem_gb=memcalc.series_std_gb * 3,
    )
    workflow.connect(inputnode, "bold_std", computedvars, "in_file")
    workflow.connect(inputnode, "bold_mask_std", computedvars, "in_mask")

    outliers = pe.Node(
        afni.OutlierCount(fraction=True, out_file="outliers.out"),
        name="outliers",
        mem_gb=memcalc.series_std_gb * 2.5,
    )
    workflow.connect(inputnode, "bold_std", outliers, "in_file")
    workflow.connect(inputnode, "bold_mask_std", outliers, "mask")

    spmask = pe.Node(
        niu.Function(
            input_names=["in_file", "in_mask"],
            output_names=["out_file", "out_plot"],
            function=spikes_mask,
        ),
        name="SpikesMask",
        mem_gb=memcalc.series_std_gb * 3.5,
    )
    workflow.connect(inputnode, "bold_std", spmask, "in_file")

    spikes_bg = pe.Node(
        Spikes(no_zscore=True, detrend=False),
        name="SpikesFinderBgMask",
        mem_gb=memcalc.series_std_gb * 2.5,
    )
    workflow.connect(inputnode, "bold_std", spikes_bg, "in_file")
    workflow.connect(spmask, "out_file", spikes_bg, "in_mask")

    bigplot = pe.Node(FMRISummary(), name="BigPlot", mem_gb=memcalc.series_std_gb * 3.5)
    bigplot.inputs.fd_thres = mriqcconfig.workflow.fd_thres
    bigplot.inputs.in_segm = get_template("MNI152NLin2009cAsym", resolution=2, desc="carpet", suffix="dseg")
    workflow.connect(inputnode, "bold_std", bigplot, "in_func")
    workflow.connect(inputnode, "bold_mask_std", bigplot, "in_mask")

    workflow.connect(spikes_bg, "out_tsz", bigplot, "in_spikes_bg")
    workflow.connect(fdisp, "out_file", bigplot, "fd")
    workflow.connect(computedvars, "out_all", bigplot, "dvars")
    workflow.connect(outliers, "out_file", bigplot, "outliers")

    workflow.connect(bigplot, "out_file", make_resultdicts, "carpetplot")
