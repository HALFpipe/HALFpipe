# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path

import nibabel as nib
import nipype.pipeline.engine as pe
import numpy as np
import pytest
from halfpipe.resource import get as get_resource
from halfpipe.utils.nipype import run_workflow
from halfpipe.workflows.post_processing.bandpass_filter import init_bandpass_filter_wf
from nilearn.image import new_img_like
from scipy.signal import welch

from ...resource import setup as setup_test_resources


@pytest.mark.parametrize(
    "bandpass_filter",
    [
        ("gaussian", None, 128),
        ("gaussian", 16, None),
        ("gaussian", 16, 128),
        ("frequency_based", None, 0.1),
        ("frequency_based", 0.01, None),
        ("frequency_based", 0.01, 0.1),
    ],
)
def test_bandpass_filter_volume(tmp_path: Path, bandpass_filter: tuple[str, float | None, float | None]) -> None:
    os.chdir(str(tmp_path))

    setup_test_resources()

    image_file = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")
    mask_file = tmp_path / "mask.nii.gz"

    image = nib.nifti1.load(image_file)
    zooms: tuple[float, ...] = image.header.get_zooms()

    sampling_period: float = float(zooms[3])  # type: ignore
    sampling_frequency = 1 / sampling_period

    image_data = image.get_fdata()
    mask_data = image_data.std(axis=3) > 0

    mask_image = new_img_like(image, data=mask_data)
    nib.loadsave.save(mask_image, mask_file)

    _, before = welch(image_data[mask_data, :].ravel(), sampling_frequency)

    wf = init_bandpass_filter_wf(
        bandpass_filter,
    )
    wf.base_dir = tmp_path

    inputnode = wf.get_node("inputnode")
    assert isinstance(inputnode, pe.Node)

    inputnode.inputs.files = [str(image_file)]
    inputnode.inputs.mask = str(mask_file)
    inputnode.inputs.repetition_time = sampling_period

    graph = run_workflow(wf)

    (merge,) = [n for n in graph.nodes if n.name == "add_means"]
    (out_file,) = merge.result.outputs.out_file

    image = nib.nifti1.load(out_file)
    image_data = image.get_fdata()

    _, after = welch(image_data[mask_data, :].ravel(), sampling_frequency)
    assert np.any(after < before)
