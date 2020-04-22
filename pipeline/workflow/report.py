# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.algorithms import confounds as nac

from niworkflows.interfaces.masks import SimpleShowMaskRPT  # ROIsPlot
from ..interface import PlotRegistration, PlotEpi, BoldFileReportMetadata, ResampleIfNeeded

from .memory import MemoryCalculator
from .utils import ConnectAttrlistHelper

in_attrs_from_anat_preproc_wf_direct = ["t1w_preproc", "t1w_mask", "t1w_dseg"]
in_attrs_from_anat_preproc_wf_keyselect = [
    "std_preproc",
    "std_mask",
    "std_dseg",
]
in_attrs_from_anat_preproc_wf = (
    in_attrs_from_anat_preproc_wf_direct + in_attrs_from_anat_preproc_wf_keyselect
)

in_attrs_from_func_preproc_wf_direct = ["aroma_metadata", "aroma_report"]
in_attrs_from_func_preproc_wf_keyselect = [
    "bold_std",
    "bold_std_ref",
    "bold_mask_std",
]
in_attrs_from_func_preproc_wf = (
    in_attrs_from_func_preproc_wf_direct + in_attrs_from_func_preproc_wf_keyselect
)

target_space = "MNI152NLin6Asym"

connect_report_wf_attrs_from_anat_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_anat_preproc_wf_direct,
    keyAttr="outputnode.template",
    keyVal=target_space,
    keySelectAttrs=in_attrs_from_anat_preproc_wf_keyselect,
)
connect_report_wf_attrs_from_func_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_func_preproc_wf_direct,
    keyAttr="inputnode.template",
    keyVal=target_space,
    keySelectAttrs=in_attrs_from_func_preproc_wf_keyselect,
)

in_attrs_from_filt_wf = ["out3"]

connect_report_wf_attrs_from_filt_wf = ConnectAttrlistHelper(in_attrs_from_filt_wf)


def init_report_wf(name="report_wf", memcalc=MemoryCalculator()):
    """

    """
    workflow = pe.Workflow(name=name)

    # only input is the bold image
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                *in_attrs_from_anat_preproc_wf,
                *in_attrs_from_func_preproc_wf,
                *in_attrs_from_filt_wf,
                "metadata",
            ]
        ),
        name="inputnode",
    )

    # output is an image file for display in the qualitycheck web page
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["resultdicts", "metadata"]), name="outputnode"
    )

    # T1w segmentation
    seg_rpt = pe.Node(SimpleShowMaskRPT(), name="seg_rpt")
    workflow.connect(
        [
            (
                inputnode,
                seg_rpt,
                [("t1w_preproc", "background_file"), ("t1w_mask", "mask_file")],
            )
        ]
    )

    # T1->mni
    t1_norm_rpt = pe.Node(PlotRegistration(), name="t1_norm_rpt", mem_gb=0.1)
    workflow.connect(
        [(inputnode, t1_norm_rpt, [("std_preproc", "in_file"), ("std_mask", "mask_file")],)]
    )

    # EPI->mni
    epi_norm_rpt = pe.Node(PlotRegistration(), name="epi_norm_rpt", mem_gb=0.1)
    workflow.connect(
        [
            (
                inputnode,
                epi_norm_rpt,
                [("bold_std_ref", "in_file"), ("bold_mask_std", "mask_file")],
            )
        ]
    )

    # calculate the tsnr image
    tsnr = pe.Node(interface=nac.TSNR(), name="compute_tsnr", mem_gb=memcalc.series_std_gb)
    workflow.connect([(inputnode, tsnr, [("bold_std", "in_file")])])

    # plot the tsnr image
    plot_tsnr = pe.Node(interface=PlotEpi(), name="plot_tsnr", mem_gb=memcalc.min_gb)
    workflow.connect(
        [
            (inputnode, plot_tsnr, [("bold_mask_std", "mask_file")]),
            (tsnr, plot_tsnr, [("tsnr_file", "in_file")]),
        ]
    )

    # carpetplot

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
    #
    # makeresultdicts = pe.Node(
    #     interface=MakeResultdicts(
    #         keys=[
    #             "firstlevelanalysisname",
    #             "firstlevelfeaturename",
    #             "cope",
    #             "varcope",
    #             "zstat",
    #             "dof_file",
    #             "mask_file",
    #         ]
    #     ),
    #     name="makeresultdicts",
    # )

    return workflow
