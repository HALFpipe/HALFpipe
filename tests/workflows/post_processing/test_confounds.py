import os
from pathlib import Path

import nibabel as nib
import nipype.pipeline.engine as pe
import numpy as np
import pandas as pd
from nilearn.image import new_img_like

from halfpipe.resource import get as get_resource
from halfpipe.utils.nipype import run_workflow
from halfpipe.workflows.post_processing.confounds import init_confounds_regression_wf

from ...resource import setup as setup_test_resources


def test_confounds_regression_wf_empty(tmp_path: Path) -> None:
    rng = np.random.default_rng()

    # Go to temporary directory
    os.chdir(str(tmp_path))

    # Create workflow object
    workflow = init_confounds_regression_wf()
    workflow.base_dir = tmp_path

    # Retrieve inputnode so that we can set its inputs
    inputnode = workflow.get_node("inputnode")
    assert isinstance(inputnode, pe.Node)

    # Get test image from online resources
    setup_test_resources()
    image_file = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")

    # Load image to generate mask
    image = nib.nifti1.load(image_file)
    image_data = image.get_fdata()
    mask_data = image_data.std(axis=3) > 0
    mask_image = new_img_like(image, data=mask_data, copy_header=True)

    # Save mask to file
    mask_file = tmp_path / "mask.nii.gz"
    nib.loadsave.save(mask_image, mask_file)

    # Set the workflow inputs on the inputnode
    inputnode.inputs.bold = str(image_file)
    inputnode.inputs.mask = str(mask_file)

    # Generate confounds
    _, _, _, volume_count = image.shape
    confounds = pd.DataFrame(
        dict(
            a=rng.random(size=(volume_count,)),
            b=rng.random(size=(volume_count,)),
            c=rng.random(size=(volume_count,)),
        )
    )
    confounds_file = tmp_path / "confounds.txt"
    confounds.to_csv(confounds_file, sep="\t", index=False, na_rep="n/a")
    inputnode.inputs.confounds = str(confounds_file)

    confounds_selected_file = tmp_path / "confounds-selected.txt"
    pd.DataFrame().to_csv(confounds_selected_file, sep="\t", index=False, na_rep="n/a")
    inputnode.inputs.confounds_selected = str(confounds_selected_file)

    inputnode.inputs.vals = dict()

    graph = run_workflow(workflow)

    # Retrieve relevant nodes so that we can check their outputs.
    (filter_regressor_bold,) = (n for n in graph.nodes if n.name == "filter_regressor_bold")
    (filter_regressor_confounds,) = (n for n in graph.nodes if n.name == "filter_regressor_confounds")

    # Check outputs
    pd.testing.assert_frame_equal(
        pd.read_csv(filter_regressor_confounds.result.outputs.out_file, sep="\t"),
        confounds,
    )
    filtered_image = nib.nifti1.load(filter_regressor_bold.result.outputs.out_file)
    np.testing.assert_allclose(filtered_image.get_fdata(), image_data)
