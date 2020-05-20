# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.algorithms import confounds as nac

from niworkflows.interfaces.masks import SimpleShowMaskRPT  # ROIsPlot
from fmriprep import config

from ..interface import (
    PlotRegistration,
    PlotEpi,
    BoldFileReportMetadata,
    ResampleIfNeeded,
    MakeResultdicts,
)

from .memory import MemoryCalculator
from .utils import make_reportnode_datasink, ConnectAttrlistHelper

in_attrs_from_anat_preproc_wf_direct = ["t1w_preproc", "t1w_mask", "t1w_dseg"]
in_attrs_from_anat_preproc_wf_keyselect = [
    "std_preproc",
    "std_mask",
    "std_dseg",
]
anat_in_attrs_from_anat_preproc_wf = (
    in_attrs_from_anat_preproc_wf_direct + in_attrs_from_anat_preproc_wf_keyselect
)
connect_anat_report_wf_attrs_from_anat_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_anat_preproc_wf_direct,
    keyAttr="outputnode.template",
    keyVal=config.workflow.spaces.get_spaces()[0],
    keySelectAttrs=in_attrs_from_anat_preproc_wf_keyselect,
)


def init_anat_report_wf(workdir=None, name="anat_report_wf", memcalc=MemoryCalculator()):
    workflow = pe.Workflow(name=name)

    # only input is the bold image
    inputnode = pe.Node(
        niu.IdentityInterface(fields=[*anat_in_attrs_from_anat_preproc_wf, "metadata"]),
        name="inputnode",
    )
    # T1w segmentation
    skull_strip_report = pe.Node(SimpleShowMaskRPT(), name="skull_strip_report")
    workflow.connect(
        [
            (
                inputnode,
                skull_strip_report,
                [("t1w_preproc", "background_file"), ("t1w_mask", "mask_file")],
            )
        ]
    )

    # T1->mni
    t1_norm_rpt = pe.Node(
        PlotRegistration(template=config.workflow.spaces.get_spaces()[0]),
        name="t1_norm_rpt",
        mem_gb=0.1,
    )
    workflow.connect(
        [(inputnode, t1_norm_rpt, [("std_preproc", "in_file"), ("std_mask", "mask_file")],)]
    )

    mergereport = pe.Node(interface=niu.Merge(2), name="mergereport", run_without_submitting=True,)
    workflow.connect(
        [
            (skull_strip_report, mergereport, [("out_report", "in1")]),
            (t1_norm_rpt, mergereport, [("out_report", "in2")]),
        ]
    )

    reportnode = pe.Node(interface=MakeResultdicts(keys=["desc", "report"]), name="reportnode")
    reportnode.inputs.desc = ["skull_strip_report", "t1_norm_rpt"]
    workflow.connect(inputnode, "metadata", reportnode, "basedict")
    workflow.connect(mergereport, "out", reportnode, "report")

    assert workdir is not None
    make_reportnode_datasink(workflow, workdir)

    return workflow


in_attrs_from_anat_preproc_wf_keyselect = ["std_dseg"]
func_in_attrs_from_anat_preproc_wf = in_attrs_from_anat_preproc_wf_keyselect
connect_func_report_wf_attrs_from_anat_preproc_wf = ConnectAttrlistHelper(
    [],
    keyAttr="outputnode.template",
    keyVal=config.workflow.spaces.get_spaces()[0],
    keySelectAttrs=in_attrs_from_anat_preproc_wf_keyselect,
)

in_attrs_from_func_preproc_wf_direct = ["aroma_metadata"]
in_attrs_from_func_preproc_wf_keyselect = [
    "bold_std",
    "bold_std_ref",
    "bold_mask_std",
]
in_attrs_from_func_preproc_wf = (
    in_attrs_from_func_preproc_wf_direct + in_attrs_from_func_preproc_wf_keyselect
)
connect_func_report_wf_attrs_from_func_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_func_preproc_wf_direct,
    keyAttr="inputnode.template",
    keyVal=config.workflow.spaces.get_spaces()[0],
    keySelectAttrs=in_attrs_from_func_preproc_wf_keyselect,
)

in_attrs_from_filt_wf = ["out3"]
connect_func_report_wf_attrs_from_filt_wf = ConnectAttrlistHelper(in_attrs_from_filt_wf)


def init_func_report_wf(workdir=None, name="func_report_wf", memcalc=MemoryCalculator()):
    """

    """
    workflow = pe.Workflow(name=name)

    # only input is the bold image
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                *func_in_attrs_from_anat_preproc_wf,
                *in_attrs_from_func_preproc_wf,
                *in_attrs_from_filt_wf,
                "metadata",
            ]
        ),
        name="inputnode",
    )

    # output is an image file for display in the qualitycheck web page
    outputnode = pe.Node(niu.IdentityInterface(fields=["metadata"]), name="outputnode")

    # EPI->mni
    epi_norm_rpt = pe.Node(
        PlotRegistration(template=config.workflow.spaces.get_spaces()[0]),
        name="epi_norm_rpt",
        mem_gb=0.1,
    )
    workflow.connect(
        [(inputnode, epi_norm_rpt, [("bold_std_ref", "in_file"), ("bold_mask_std", "mask_file")],)]
    )

    # calculate the tsnr image
    tsnr = pe.Node(interface=nac.TSNR(), name="compute_tsnr", mem_gb=memcalc.series_std_gb)
    workflow.connect([(inputnode, tsnr, [("bold_std", "in_file")])])

    # plot the tsnr image
    tsnr_rpt = pe.Node(interface=PlotEpi(), name="tsnr_rpt", mem_gb=memcalc.min_gb)
    workflow.connect(
        [
            (inputnode, tsnr_rpt, [("bold_mask_std", "mask_file")]),
            (tsnr, tsnr_rpt, [("tsnr_file", "in_file")]),
        ]
    )

    # reportnode
    mergereport = pe.Node(interface=niu.Merge(2), name="mergereport", run_without_submitting=True,)
    workflow.connect(epi_norm_rpt, "out_report", mergereport, "in1")
    workflow.connect(tsnr_rpt, "out_report", mergereport, "in2")

    reportnode = pe.Node(interface=MakeResultdicts(keys=["desc", "report"]), name="reportnode")
    reportnode.inputs.desc = ["epi_norm_rpt", "tsnr_rpt"]
    workflow.connect(inputnode, "metadata", reportnode, "basedict")
    workflow.connect(mergereport, "out", reportnode, "report")

    # metrics
    resampleifneeded = pe.Node(
        interface=ResampleIfNeeded(method="nearest"),
        name="resampleifneeded",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "std_dseg", resampleifneeded, "in_file")
    workflow.connect(inputnode, "bold_std", resampleifneeded, "ref_file")
    reportmetadata = pe.Node(
        interface=BoldFileReportMetadata(), name="reportmetadata", mem_gb=memcalc.series_std_gb
    )
    workflow.connect(inputnode, "metadata", reportmetadata, "basedict")
    workflow.connect(inputnode, "out3", reportmetadata, "confounds")
    workflow.connect(tsnr, "tsnr_file", reportmetadata, "tsnr_file")
    workflow.connect(inputnode, "aroma_metadata", reportmetadata, "aroma_metadata")
    workflow.connect(resampleifneeded, "out_file", reportmetadata, "dseg")
    workflow.connect(reportmetadata, "outdict", outputnode, "metadata")

    assert workdir is not None
    make_reportnode_datasink(workflow, workdir)

    return workflow
