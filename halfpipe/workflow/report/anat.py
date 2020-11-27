# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe

from niworkflows.interfaces.masks import SimpleShowMaskRPT  # ROIsPlot
from fmriprep import config

from ...interface import Exec, PlotRegistration, MakeResultdicts, ResultdictDatasink

from ..memory import MemoryCalculator


def init_anat_report_wf(workdir=None, name="anat_report_wf", memcalc=MemoryCalculator()):
    workflow = pe.Workflow(name=name)

    fmriprepreports = ["t1w_dseg_mask", "std_t1w"]
    fmriprepreportdatasinks = [f"ds_{fr}_report" for fr in fmriprepreports]
    strfields = [
        "t1w_preproc",
        "t1w_mask",
        "t1w_dseg",
        "std_preproc",
        "std_mask",
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
        MakeResultdicts(reportkeys=["skull_strip_report", "t1_norm_rpt", *fmriprepreports]),
        name="make_resultdicts",
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    for fr, frd in zip(fmriprepreports, fmriprepreportdatasinks):
        workflow.connect(inputnode, frd, make_resultdicts, fr)

    # T1w segmentation
    skull_strip_report = pe.Node(SimpleShowMaskRPT(), name="skull_strip_report")
    workflow.connect(inputnode, "t1w_preproc", skull_strip_report, "background_file")
    workflow.connect(inputnode, "t1w_mask", skull_strip_report, "mask_file")
    workflow.connect(skull_strip_report, "out_report", make_resultdicts, "skull_strip_report")

    # T1 -> mni
    t1_norm_rpt = pe.Node(
        PlotRegistration(template=config.workflow.spaces.get_spaces()[0]),
        name="t1_norm_rpt",
        mem_gb=0.1,
    )
    workflow.connect(inputnode, "std_preproc", t1_norm_rpt, "in_file")
    workflow.connect(inputnode, "std_mask", t1_norm_rpt, "mask_file")
    workflow.connect(t1_norm_rpt, "out_report", make_resultdicts, "t1_norm_rpt")

    return workflow
