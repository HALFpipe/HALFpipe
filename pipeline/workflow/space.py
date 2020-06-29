# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from smriprep.interfaces.templateflow import TemplateFlowSelect
from niworkflows.interfaces.utility import KeySelect

from ..interface import FixInputApplyTransforms as ApplyTransforms
from ..utils import first


def add_templates_by_composing_transforms(workflow, templates=["MNI152NLin6Asym"]):
    anat_norm_wf = workflow.get_node("anat_norm_wf")
    outputnode = workflow.get_node("outputnode")

    if len(templates) == 0:
        workflow.connect(
            [
                (
                    anat_norm_wf,
                    outputnode,
                    [
                        ("outputnode.standardized", "std_preproc"),
                        ("outputnode.std_mask", "std_mask"),
                        ("outputnode.std_dseg", "std_dseg"),
                        ("outputnode.std_tpms", "std_tpms"),
                        ("outputnode.template", "template"),
                        ("outputnode.anat2std_xfm", "anat2std_xfm"),
                        ("outputnode.std2anat_xfm", "std2anat_xfm"),
                    ],
                ),
            ]
        )
        return

    templitersrc = pe.Node(
        niu.IdentityInterface(fields=["template"]),
        iterables=[("template", templates)],
        name="templitersrc",
    )

    movingsrc = pe.Node(
        niu.IdentityInterface(
            fields=["moving_image", "moving_mask", "moving_segmentation", "moving_tpms"]
        ),
        name="movingsrc",
    )
    brain_extraction_wf = workflow.get_node("brain_extraction_wf")
    if brain_extraction_wf is None:
        brain_extraction_wf = workflow.get_node("n4_only_wf")
    workflow.connect(
        [
            (
                brain_extraction_wf,
                movingsrc,
                [(("outputnode.bias_corrected", first), "moving_image")],
            ),
            (workflow.get_node("buffernode"), movingsrc, [("t1w_mask", "moving_mask")]),
            (
                workflow.get_node("t1w_dseg"),
                movingsrc,
                [("tissue_class_map", "moving_segmentation")],
            ),
            (workflow.get_node("t1w_dseg"), movingsrc, [("probability_maps", "moving_tpms")]),
        ]
    )

    # gather inputs

    def select_xfm_to_compose(base_template_list=None, out_template=None):
        from pipeline import resources

        for base_template in base_template_list:
            xfm_file = resources.get(f"tpl_{out_template}_from_{base_template}_mode_image_xfm.h5")
            inv_xfm_file = resources.get(
                f"tpl_{base_template}_from_{out_template}_mode_image_xfm.h5"
            )
            if xfm_file is not None and inv_xfm_file is not None:
                return base_template, xfm_file, inv_xfm_file
        raise ValueError("No xfm available")

    selectcompxfm = pe.Node(
        interface=niu.Function(
            input_names=["base_template_list", "out_template"],
            output_names=["base_template", "xfm", "inv_xfm"],
            function=select_xfm_to_compose,
        ),
        name="selectcompxfm",
    )
    workflow.connect(anat_norm_wf, "outputnode.template", selectcompxfm, "base_template_list")
    workflow.connect(templitersrc, "template", selectcompxfm, "out_template")

    selectbasexfm = pe.Node(
        KeySelect(fields=["anat2std_xfm", "std2anat_xfm"]),
        name="selectbasexfm",
        run_without_submitting=True,
    )
    workflow.connect(selectcompxfm, "base_template", selectbasexfm, "key")
    workflow.connect(anat_norm_wf, "outputnode.template", selectbasexfm, "keys")
    workflow.connect(anat_norm_wf, "outputnode.anat2std_xfm", selectbasexfm, "anat2std_xfm")
    workflow.connect(anat_norm_wf, "outputnode.std2anat_xfm", selectbasexfm, "std2anat_xfm")

    tf_select = pe.Node(
        TemplateFlowSelect(resolution=1), name="tf_select", run_without_submitting=True
    )
    workflow.connect(templitersrc, "template", tf_select, "template")

    # compose xfms

    mergexfm = pe.Node(niu.Merge(numinputs=2), name="mergexfm", run_without_submitting=True)
    workflow.connect(selectbasexfm, "anat2std_xfm", mergexfm, "in1")
    workflow.connect(selectcompxfm, "xfm", mergexfm, "in2")

    compxfm = pe.Node(
        ApplyTransforms(
            dimension=3,
            print_out_composite_warp_file=True,
            output_image="ants_t1_to_mniComposite.nii.gz",
        ),
        name="compxfm",
    )
    workflow.connect(tf_select, "t1w_file", compxfm, "reference_image")
    workflow.connect(mergexfm, "out", compxfm, "transforms")

    mergeinvxfm = pe.Node(niu.Merge(numinputs=2), name="mergeinvxfm", run_without_submitting=True)
    workflow.connect(selectcompxfm, "inv_xfm", mergeinvxfm, "in1")
    workflow.connect(selectbasexfm, "std2anat_xfm", mergeinvxfm, "in2")

    compinvxfm = pe.Node(
        ApplyTransforms(
            dimension=3,
            print_out_composite_warp_file=True,
            output_image="ants_t1_to_mniInverseComposite.nii.gz",
        ),
        name="compinvxfm",
    )
    workflow.connect(movingsrc, "moving_image", compinvxfm, "reference_image")
    workflow.connect(mergeinvxfm, "out", compinvxfm, "transforms")

    # apply xfms

    tpl_moving = pe.Node(
        ApplyTransforms(
            dimension=3, default_value=0, float=True, interpolation="LanczosWindowedSinc"
        ),
        name="tpl_moving",
    )
    workflow.connect(movingsrc, "moving_image", tpl_moving, "input_image")
    workflow.connect(tf_select, "t1w_file", tpl_moving, "reference_image")
    workflow.connect(compxfm, "output_image", tpl_moving, "transforms")

    std_mask = pe.Node(
        ApplyTransforms(dimension=3, default_value=0, float=True, interpolation="MultiLabel"),
        name="std_mask",
    )
    workflow.connect(movingsrc, "moving_mask", std_mask, "input_image")
    workflow.connect(tf_select, "t1w_file", std_mask, "reference_image")
    workflow.connect(compxfm, "output_image", std_mask, "transforms")

    std_dseg = pe.Node(
        ApplyTransforms(dimension=3, default_value=0, float=True, interpolation="MultiLabel"),
        name="std_dseg",
    )
    workflow.connect(movingsrc, "moving_segmentation", std_dseg, "input_image")
    workflow.connect(tf_select, "t1w_file", std_dseg, "reference_image")
    workflow.connect(compxfm, "output_image", std_dseg, "transforms")

    std_tpms = pe.MapNode(
        ApplyTransforms(dimension=3, default_value=0, float=True, interpolation="Gaussian"),
        iterfield=["input_image"],
        name="std_tpms",
    )
    workflow.connect(movingsrc, "moving_tpms", std_tpms, "input_image")
    workflow.connect(tf_select, "t1w_file", std_tpms, "reference_image")
    workflow.connect(compxfm, "output_image", std_tpms, "transforms")

    # merge

    mergefields = [
        "template",
        "standardized",
        "std_mask",
        "std_dseg",
        "std_tpms",
        "anat2std_xfm",
        "std2anat_xfm",
    ]
    aliases = {"standardized": "std_preproc"}

    joinnode = pe.JoinNode(
        niu.IdentityInterface(fields=mergefields),
        name="joinnode",
        joinsource="templitersrc",
        joinfield="template",
    )
    workflow.connect(templitersrc, "template", joinnode, "template")
    workflow.connect(compxfm, "output_image", joinnode, "anat2std_xfm")
    workflow.connect(compinvxfm, "output_image", joinnode, "std2anat_xfm")
    workflow.connect(tpl_moving, "output_image", joinnode, "standardized")
    workflow.connect(std_mask, "output_image", joinnode, "std_mask")
    workflow.connect(std_dseg, "output_image", joinnode, "std_dseg")
    workflow.connect(std_tpms, "output_image", joinnode, "std_tpms")

    for field in mergefields:
        merge = pe.Node(niu.Merge(numinputs=2), name=f"merge{field}", run_without_submitting=True)
        workflow.connect(anat_norm_wf, f"outputnode.{field}", merge, "in1")
        workflow.connect(joinnode, field, merge, "in2")

        workflow.connect(merge, "out", outputnode, aliases[field] if field in aliases else field)
