# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path

import nibabel as nib
import nipype.pipeline.engine as pe
import numpy as np
from halfpipe.resource import get as get_resource
from halfpipe.utils.nipype import run_workflow
from halfpipe.workflows.post_processing.grand_mean_scaling import (
    init_grand_mean_scaling_wf,
)
from nilearn.image import new_img_like

from ...resource import setup as setup_test_resources


def test_grand_mean_scaling_volume(tmp_path: Path) -> None:
    # Go to temporary directory
    os.chdir(str(tmp_path))

    # Get test image from online resources
    setup_test_resources()
    image_file = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")

    # Load image to generate mask
    image = nib.nifti1.load(image_file)
    image_data = image.get_fdata()
    mask_data = image_data.std(axis=3) > 0
    mask_image = new_img_like(image, data=mask_data)

    # Save mask to file
    mask_file = tmp_path / "mask.nii.gz"
    nib.loadsave.save(mask_image, mask_file)

    # Create workflow object
    target_mean = 1e4
    wf = init_grand_mean_scaling_wf(mean=target_mean)
    wf.base_dir = tmp_path

    # Retrieve inputnode so that we can set its inputs
    inputnode = wf.get_node("inputnode")
    assert isinstance(inputnode, pe.Node)

    # Set the workflow inputs on the inputnode
    inputnode.inputs.files = [str(image_file)]
    inputnode.inputs.mask = str(mask_file)

    graph = run_workflow(wf)

    # Retrieve the grand mean scaling node so that we can check its outputs.
    # We cannot retrieve the outputnode because that is optimized out by
    # Nipype
    (merge,) = [n for n in graph.nodes if n.name == "grand_mean_scaling"]

    # Check outputs
    assert len(merge.result.outputs.files) == 1
    (out_file,) = merge.result.outputs.files

    out_image = nib.nifti1.load(out_file)
    out_data = out_image.get_fdata()

    assert np.isclose(out_data[mask_data, :].mean(), target_mean)
