# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from fmriprep import config
from fmriprep.workflows.bold.apply import init_bold_volumetric_resample_wf
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from niworkflows.utils.spaces import Reference, SpatialReferences

from ...resource import get as get_resource
from ..constants import Constants
from ..memory import MemoryCalculator


def init_alt_bold_std_trans_wf(
    name="alt_bold_std_trans_wf",
    spaces: SpatialReferences | None = None,
    memcalc: MemoryCalculator | None = None,
):
    """
    This workflow is needed to run ICA_AROMA.
    """
    spaces = SpatialReferences(Reference.from_string("MNI152NLin6Asym:res-2"), checkpoint=True) if spaces is None else spaces
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_file",
                "bold_mask",
                "itk_bold_to_t1",
                "out_warp",
                "anat2std_xfm",
                "xforms",
            ]
        ),
        name="inputnode",
    )

    bold_std_trans_wf_outputs = ["bold_file", "resampling_reference"]
    outputnode = pe.Node(
        niu.IdentityInterface(fields=[f"alt_{a}" for a in bold_std_trans_wf_outputs]),
        name="outputnode",
    )

    #
    alt_reference_spaces = spaces.get_spaces(nonstandard=False, dim=(3,))

    #
    mergexfm = pe.MapNode(niu.Merge(numinputs=2), iterfield="in1", name="mergexfm")
    mergexfm.inputs.in1 = [
        get_resource(f"tpl_{alt}_from_{Constants.reference_space}_mode_image_xfm.h5") for alt in alt_reference_spaces
    ]
    workflow.connect(inputnode, "anat2std_xfm", mergexfm, "in2")

    bold_std_trans_wf = init_bold_volumetric_resample_wf(
        metadata={},  # We pass empty metadata so we can reuse workflow between subjects
        jacobian=True,  # TODO: True or false? no documentation in FMRIPREP https://github.com/nipreps/fmriprep/blob/master/fmriprep/workflows/bold/apply.py#L19
        mem_gb={"resampled": memcalc.volume_std_gb},  # was memcalc.volume_std_gb
        omp_nthreads=config.nipype.omp_nthreads,
        name="bold_volumetric_resample_wf",
    )

    bold_std_trans_wf_inputnode = bold_std_trans_wf.get_node("inputnode")
    assert isinstance(bold_std_trans_wf_inputnode, pe.Node)
    bold_std_trans_wf_inputnode.inputs.templates = ["MNI152NLin6Asym"]

    workflow.connect(mergexfm, "out", bold_std_trans_wf, "inputnode.anat2std_xfm")  # same
    workflow.connect(inputnode, "bold_file", bold_std_trans_wf, "inputnode.bold_file")
    workflow.connect(inputnode, "xforms", bold_std_trans_wf, "inputnode.motion_xfm")  # was hmc_xforms
    workflow.connect(inputnode, "itk_bold_to_t1", bold_std_trans_wf, "inputnode.boldref2anat_xfm")  # was itk_bold_to_t1
    workflow.connect(inputnode, "bold_mask", bold_std_trans_wf, "inputnode.target_mask")  # used differently?
    # workflow.connect(inputnode, "out_warp", bold_std_trans_wf, "inputnode.fieldwarp")

    for a in bold_std_trans_wf_outputs:
        workflow.connect(bold_std_trans_wf, f"outputnode.{a}", outputnode, f"alt_{a}")

    return workflow
