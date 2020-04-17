# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from smriprep.workflows.norm import init_anat_norm_wf
from niworkflows.anat.ants import init_brain_extraction_wf
from niworkflows.interfaces.images import ValidateImage

from ...fmriprepconfig import config as fmriprepconfig
from ...utils import first


def init_anat_preproc_wf(name="anat_preproc_wf"):
    """
    simplified from smriprep/workflows/anatomical.py
    """

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=["t1w"]), name="inputnode")

    buffernode = pe.Node(
        niu.IdentityInterface(fields=["t1w_brain", "t1w_mask"]), name="buffernode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "t1w_preproc",
                "t1w_mask",
                "t1w_dseg",
                "t1w_tpms",
                "std_preproc",
                "std_mask",
                "std_dseg",
                "std_tpms",
                "template",
                "anat2std_xfm",
                "std2anat_xfm",
            ],
        ),
        name="outputnode",
    )

    # Step 1
    anat_validate = pe.Node(ValidateImage(), name="anat_validate", run_without_submitting=True)
    brain_extraction_wf = init_brain_extraction_wf(
        in_template=fmriprepconfig.skull_strip_template.space,
        template_spec=fmriprepconfig.skull_strip_template.spec,
        atropos_use_random_seed=True,
        omp_nthreads=fmriprepconfig.omp_nthreads,
        normalization_quality="precise",
    )
    workflow.connect(
        [
            (inputnode, anat_validate, [("t1w", "in_file")]),
            (anat_validate, brain_extraction_wf, [("out_file", "inputnode.in_files")]),
            (brain_extraction_wf, outputnode, [("outputnode.bias_corrected", "t1w_preproc")],),
            (
                brain_extraction_wf,
                buffernode,
                [
                    (("outputnode.out_file", first), "t1w_brain"),
                    ("outputnode.out_mask", "t1w_mask"),
                ],
            ),
            (buffernode, outputnode, [("t1w_brain", "t1w_brain"), ("t1w_mask", "t1w_mask")],),
        ]
    )

    # Step 2
    t1w_dseg = pe.Node(
        fsl.FAST(segments=True, no_bias=True, probability_maps=True),
        name="t1w_dseg",
        mem_gb=3,
    )
    workflow.connect(
        [
            (buffernode, t1w_dseg, [("t1w_brain", "in_files")]),
            (
                t1w_dseg,
                outputnode,
                [("tissue_class_map", "t1w_dseg"), ("probability_maps", "t1w_tpms")],
            ),
        ]
    )

    # Step 3
    anat_norm_wf = init_anat_norm_wf(
        debug=fmriprepconfig.debug,
        omp_nthreads=fmriprepconfig.omp_nthreads,
        templates=fmriprepconfig.spaces.get_spaces(nonstandard=False, dim=(3,)),
    )
    workflow.connect(
        [
            (inputnode, anat_norm_wf, [("t1w", "inputnode.orig_t1w")],),
            (
                brain_extraction_wf,
                anat_norm_wf,
                [(("outputnode.bias_corrected", first), "inputnode.moving_image")],
            ),
            (buffernode, anat_norm_wf, [("t1w_mask", "inputnode.moving_mask")]),
            (t1w_dseg, anat_norm_wf, [("tissue_class_map", "inputnode.moving_segmentation")],),
            (t1w_dseg, anat_norm_wf, [("probability_maps", "inputnode.moving_tpms")]),
            (
                anat_norm_wf,
                outputnode,
                [
                    ("poutputnode.standardized", "std_preproc"),
                    ("poutputnode.std_mask", "std_mask"),
                    ("poutputnode.std_dseg", "std_dseg"),
                    ("poutputnode.std_tpms", "std_tpms"),
                    ("outputnode.template", "template"),
                    ("outputnode.anat2std_xfm", "anat2std_xfm"),
                    ("outputnode.std2anat_xfm", "std2anat_xfm"),
                ],
            ),
        ]
    )

    return workflow
