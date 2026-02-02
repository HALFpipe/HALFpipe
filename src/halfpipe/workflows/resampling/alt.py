# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any

from fmriprep import config
from fmriprep.workflows.bold.apply import init_bold_volumetric_resample_wf
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from smriprep.interfaces.templateflow import fetch_template_files

from ...interfaces.fixes.applytransforms import ApplyTransforms
from ...resource import get as get_resource
from ..configurables import configurables
from ..memory import MemoryCalculator


def init_alt_bold_std_trans_wf(
    name="alt_bold_std_trans_wf",
    alt_reference_space: str = "MNI152NLin6Asym",
    alt_reference_specs: dict[str, Any] | None = None,
    memcalc: MemoryCalculator | None = None,
):
    """
    This workflow is needed to run ICA_AROMA.
    This workflow will be run by default even when ICA_AROMA is not wanted
    because users still want the QC report.

    We do this because we need an extra transform added, which we do in the mergexfm done.
    This extra transform also needs to be applied to the mask at ica_components_wf,
    since the resampled mask used to be outputted by fmriprep but not anymore.

    """

    # Handle mutable default arguments
    if alt_reference_specs is None:
        alt_reference_specs = dict(res=2)
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc

    workflow = pe.Workflow(name=name)

    # see this
    # https://github.com/nipreps/fmriprep/blob/b6c7b953bb0a07fe466aed556a21ed02ae218da5/fmriprep/workflows/bold/base.py#L460C19-L460C26

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_minimal",
                "bold_mask_native",
                "coreg_boldref",  # comes from bold_fit_wf.outputnode.coreg_boldref',
                "boldref2anat_xfm",
                "anat2std_xfm",
                "motion_xfm",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=["alt_bold_file_std", "alt_bold_mask_std"]),
        name="outputnode",
    )

    # We use ravel_inputs to flatten the list, to have just a list instead of a list of lists
    mergexfm = pe.Node(niu.Merge(numinputs=2, ravel_inputs=True), name="mergexfm")
    mergexfm.inputs.in1 = get_resource(f"tpl_{alt_reference_space}_from_{configurables.reference_space}_mode_image_xfm.h5")
    workflow.connect(inputnode, "anat2std_xfm", mergexfm, "in2")  # in the fmriprep resample one this one is not there

    omp_nthreads = config.nipype.omp_nthreads
    if omp_nthreads is None:
        raise RuntimeError('"omp_nthreads" is not set in the fMRIPrep config file')
    bold_std_trans_wf = init_bold_volumetric_resample_wf(
        metadata={},  # We pass empty metadata so we can reuse workflow between subjects
        jacobian=True,  # TODO: Need to decide if we want the field map jacobian as an output
        mem_gb={"resampled": memcalc.series_std_gb},
        omp_nthreads=omp_nthreads,
        name="bold_volumetric_resample_trans_wf",
    )

    bold_std_trans_wf_inputnode = bold_std_trans_wf.get_node("inputnode")
    assert isinstance(bold_std_trans_wf_inputnode, pe.Node)

    # Derive target reference file
    template_files = fetch_template_files(alt_reference_space, specs=alt_reference_specs)
    bold_std_trans_wf_inputnode.inputs.target_ref_file = template_files["t1w"]
    bold_std_trans_wf_inputnode.inputs.target_mask = template_files["mask"]

    fmriprep_merge_node = bold_std_trans_wf.get_node("boldref2target")
    if fmriprep_merge_node is None:
        raise RuntimeError('Could not find node "boldref2target"')
    fmriprep_merge_node.inputs.ravel_inputs = True
    fmriprep_merge_node.inputs.no_flatten = False

    workflow.connect(mergexfm, "out", bold_std_trans_wf, "inputnode.anat2std_xfm")
    workflow.connect(inputnode, "bold_minimal", bold_std_trans_wf, "inputnode.bold_file")
    workflow.connect(inputnode, "coreg_boldref", bold_std_trans_wf, "inputnode.bold_ref_file")  # moving_image
    workflow.connect(inputnode, "motion_xfm", bold_std_trans_wf, "inputnode.motion_xfm")  # its a text file instead of h5
    workflow.connect(inputnode, "boldref2anat_xfm", bold_std_trans_wf, "inputnode.boldref2anat_xfm")

    workflow.connect(bold_std_trans_wf, "outputnode.bold_file", outputnode, "alt_bold_file_std")

    resample_mask = pe.Node(ApplyTransforms(interpolation="MultiLabel"), name="resample_mask")
    resample_mask.inputs.reference_image = template_files["t1w"]
    workflow.connect(inputnode, "bold_mask_native", resample_mask, "input_image")
    workflow.connect(bold_std_trans_wf, "boldref2target.out", resample_mask, "transforms")

    workflow.connect(resample_mask, "output_image", outputnode, "alt_bold_mask_std")

    return workflow
