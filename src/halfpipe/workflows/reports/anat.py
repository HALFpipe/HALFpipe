# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from niworkflows.interfaces.reportlets.masks import SimpleShowMaskRPT

from ...interfaces.reports.imageplot import PlotRegistration
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.make import MakeResultdicts
from ..constants import Constants
from ..memory import MemoryCalculator


def init_anat_report_wf(
    workdir=None,
    name="anat_report_wf",
    memcalc: MemoryCalculator | None = None,
):
    """
    We create our own report because instead of a moving display for the
    visualizations of the anatomical preprocessing, we prefer static ones.
    """

    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    workflow = pe.Workflow(name=name)

    fmriprepreports = ["t1w_dseg_mask"]
    fmriprepreportdatasinks = [f"ds_{fr}_report" for fr in fmriprepreports]

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "t1w_std",
                "mask_std",
                "template",
                "t1w_preproc",
                "t1w_mask",
                "t1w_dseg",
                *fmriprepreportdatasinks,
                "tags",
            ]
        ),
        name="inputnode",
    )

    # Map outputs into result data structure
    make_resultdicts = pe.Node(
        MakeResultdicts(reportkeys=["skull_strip_report", "t1_norm_rpt", *fmriprepreports]),
        name="make_resultdicts",
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=workdir), name="resultdict_datasink")
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    # Include fmriprep reports in the result dicts
    for fr, frd in zip(fmriprepreports, fmriprepreportdatasinks, strict=False):
        workflow.connect(inputnode, frd, make_resultdicts, fr)

    # T1w segmentation
    skull_strip_report = pe.Node(SimpleShowMaskRPT(), name="skull_strip_report")
    workflow.connect(inputnode, "t1w_preproc", skull_strip_report, "background_file")
    workflow.connect(inputnode, "t1w_mask", skull_strip_report, "mask_file")
    workflow.connect(skull_strip_report, "out_report", make_resultdicts, "skull_strip_report")

    # T1 -> mni
    t1_norm_rpt = pe.Node(
        PlotRegistration(template=Constants.reference_space),
        name="t1_norm_rpt",
        mem_gb=memcalc.min_gb,
    )
    workflow.connect(inputnode, "t1w_std", t1_norm_rpt, "in_file")
    workflow.connect(inputnode, "mask_std", t1_norm_rpt, "mask_file")
    workflow.connect(t1_norm_rpt, "out_report", make_resultdicts, "t1_norm_rpt")

    return workflow
