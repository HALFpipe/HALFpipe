# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from smriprep.workflows.norm import init_anat_norm_wf
from smriprep.workflows.outputs import init_anat_reports_wf
from smriprep.workflows.surfaces import init_surface_recon_wf
from niworkflows.anat.ants import init_brain_extraction_wf
from niworkflows.interfaces.images import ValidateImage
from niworkflows.utils.spaces import Reference
from fmriprep import config

from ..space import add_templates_by_composing_transforms

from ..utils import make_reportnode, make_reportnode_datasink
from ...utils import first

norm_templates = ["MNI152NLin2009cAsym"]
extra_templates = ["MNI152NLin6Asym"]


anat_preproc_wf_output_attrs = [
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
]


def init_anat_preproc_wf(
    workdir=None, freesurfer=False, no_compose_transforms=False, name="anat_preproc_wf"
):
    """
    modified from smriprep/workflows/anatomical.py
    """

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=["t1w", "metadata"]), name="inputnode")

    buffernode = pe.Node(niu.IdentityInterface(fields=["t1w_brain", "t1w_mask"]), name="buffernode")

    outputnode = pe.Node(
        niu.IdentityInterface(fields=anat_preproc_wf_output_attrs,), name="outputnode",
    )

    skull_strip_template = Reference.from_string(config.workflow.skull_strip_template)[0]

    # Step 1
    anat_validate = pe.Node(ValidateImage(), name="anat_validate", run_without_submitting=True)
    brain_extraction_wf = init_brain_extraction_wf(
        in_template=skull_strip_template.space,
        template_spec=skull_strip_template.spec,
        atropos_use_random_seed=not config.workflow.skull_strip_fixed_seed,
        omp_nthreads=config.nipype.omp_nthreads,
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
        fsl.FAST(segments=True, no_bias=True, probability_maps=True), name="t1w_dseg", mem_gb=3,
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
        debug=config.execution.debug,
        omp_nthreads=config.nipype.omp_nthreads,
        templates=norm_templates if not no_compose_transforms else norm_templates + extra_templates,
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
        ]
    )

    # Write outputs
    anat_reports_wf = init_anat_reports_wf(freesurfer=freesurfer, output_dir="/")
    workflow.connect(
        [
            (
                outputnode,
                anat_reports_wf,
                [
                    ("t1w_preproc", "inputnode.t1w_preproc"),
                    ("t1w_mask", "inputnode.t1w_mask"),
                    ("t1w_dseg", "inputnode.t1w_dseg"),
                ],
            ),
            (inputnode, anat_reports_wf, [("t1w", "inputnode.source_file")]),
            (
                anat_norm_wf,
                anat_reports_wf,
                [
                    ("poutputnode.template", "inputnode.template"),
                    ("poutputnode.standardized", "inputnode.std_t1w"),
                    ("poutputnode.std_mask", "inputnode.std_mask"),
                ],
            ),
        ]
    )

    # Custom

    add_templates_by_composing_transforms(
        workflow, templates=extra_templates if not no_compose_transforms else []
    )

    make_reportnode(workflow, spaces=True)
    assert workdir is not None
    make_reportnode_datasink(workflow, workdir)

    if freesurfer:

        def get_subject(dic):
            return dic.get("subject")

        # 5. Surface reconstruction (--fs-no-reconall not set)
        surface_recon_wf = init_surface_recon_wf(
            name="surface_recon_wf",
            omp_nthreads=config.nipype.omp_nthreads,
            hires=config.workflow.hires,
        )
        subjects_dir = Path(workdir) / "subjects_dir"
        subjects_dir.mkdir(parents=True, exist_ok=True)
        surface_recon_wf.get_node("inputnode").inputs.subjects_dir = str(subjects_dir)
        workflow.connect(
            [
                (
                    inputnode,
                    surface_recon_wf,
                    [(("metadata", get_subject), "inputnode.subject_id")],
                ),
                (anat_validate, surface_recon_wf, [("out_file", "inputnode.t1w")]),
                (
                    brain_extraction_wf,
                    surface_recon_wf,
                    [
                        (("outputnode.out_file", first), "inputnode.skullstripped_t1"),
                        ("outputnode.out_segm", "inputnode.ants_segs"),
                        (("outputnode.bias_corrected", first), "inputnode.corrected_t1"),
                    ],
                ),
                (
                    surface_recon_wf,
                    anat_reports_wf,
                    [
                        ("outputnode.subject_id", "inputnode.subject_id"),
                        ("outputnode.subjects_dir", "inputnode.subjects_dir"),
                    ],
                ),
            ]
        )

    return workflow
