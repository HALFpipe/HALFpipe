# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from zipfile import ZipFile

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pytest
from templateflow.api import get as get_template

from halfpipe.interfaces.image_maths.resample import Resample
from halfpipe.logging import logger
from halfpipe.resource import get as get_resource
from halfpipe.workflows.constants import constants

from ...resource import setup as setup_test_resources

# todo: move methods out of unit tests


def extract_middle_slice(img):
    img_data = img.get_fdata()
    if img_data.ndim == 3:  # Standard 3D image
        slice_index = img_data.shape[2] // 2
        return img_data[:, :, slice_index]
    elif (
        img_data.ndim == 4 and img_data.shape[-1] == 1
    ):  # 3D image with singleton dimension
        slice_index = img_data.shape[2] // 2
        return img_data[:, :, slice_index, 0]
    else:
        raise ValueError(f"Unsupported image data shape: {img_data.shape}")


def create_comparison_figure(input_img, output_img, reference_img, figure_path):
    input_slice = extract_middle_slice(input_img)
    output_slice = extract_middle_slice(output_img)
    reference_slice = extract_middle_slice(reference_img)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, slice, img_data, title in zip(
        axes,
        [input_slice, output_slice, reference_slice],
        [input_img, output_img, reference_img],
        ["Input", "Output", "Reference"],
    ):
        ax.imshow(slice.T, cmap="gray", origin="lower")
        ax.set_title(f"{title}\n Shape slice: {slice.shape} \n")
        ax.axis("off")
        ax.text(
            0.5,
            -0.1,
            f"Shape full image: {img_data.shape}",
            ha="center",
            transform=ax.transAxes,
        )

    plt.savefig(figure_path)
    plt.close()


@pytest.fixture(scope="package")
def resources(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="resources")
    os.chdir(str(tmp_path))
    setup_test_resources()
    fmriprep_path = get_resource("sub-0003_fmriprep_derivatives.zip")
    atlases_path = get_resource("atlases.zip")

    with ZipFile(fmriprep_path) as zip_file, ZipFile(atlases_path) as atlases:
        zip_file.extractall(tmp_path)
        atlases.extractall(tmp_path)

    brainnetome_path = tmp_path / "atlas-Brainnetome_dseg.nii.gz"
    transform = (
        tmp_path
        / "sub-0003"
        / "anat"
        / "sub-0003_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5"
    )
    preproc_anat = tmp_path / "sub-0003" / "anat" / "sub-0003_desc-preproc_T1w.nii.gz"

    return [preproc_anat, transform, brainnetome_path]


def test_resample(tmp_path, resources):
    """
    Tests the resample interface by resampling an atlas image to MNI152NLin2009cAsym space if it is not already in that space.
    Tests different interpolation methods
    TODO: Test with a transform file
    TODO: Test with seed map
    """

    os.chdir(str(tmp_path))

    reference_dict = dict(
        reference_space="MNI152NLin2009cAsym", reference_res=constants.reference_res
    )
    template_path = get_template(
        "MNI152NLin2009cAsym", resolution=2, desc="brain", suffix="mask"
    )
    interpolations = [
        "MultiLabel",
        "Gaussian",
        "BSpline",
        "Linear",
        # "CosineWindowedSinc",
    ]  # "Linear", "NearestNeighbor"
    output_dir = tmp_path / "output_images"
    os.makedirs(output_dir, exist_ok=True)

    for i in interpolations:
        resample = Resample(interpolation=i, **reference_dict)
        resample.inputs.input_image = str(resources[2])
        resample.inputs.reference_image = str(template_path)
        # resample.inputs.transforms = ["identity", str(t1w_files[3])]
        resample.inputs.transforms = ["identity"]

        result = resample.run()
        assert result.outputs.output_image is not None

        input_image = nib.load(resample.inputs.input_image)
        reference_image = nib.load(template_path)
        output_image: nib.nifti1.Nifti1Image = nib.load(result.outputs.output_image)

        output_image_path = output_dir / f"output_{i}.nii"
        nib.save(output_image, str(output_image_path))
        comparison_figure_path = output_dir / f"comparison_{i}.png"
        create_comparison_figure(
            input_image, output_image, reference_image, str(comparison_figure_path)
        )

        logger.info(f"Saved output image for {i} at {output_image_path}")
        logger.info(f"Saved comparison figure for {i} at {comparison_figure_path}")

        # General assertions
        assert output_image.shape[:3] == reference_image.shape[:3], (
            "Image dimensions do not match for interpolation" + i
        )
        np.testing.assert_allclose(
            output_image.affine, reference_image.affine, atol=1e-2, rtol=1e-2
        ), "Affine matrices do not match for interpolation" + i

        # Interpolation specific assertions
        # if i in ["Gaussian", "BSpline"]:
        #     assert np.std(output_image.get_fdata()) < np.std(
        #         input_image.get_fdata()
        #     ), "Output should be smoother for Gaussian/BSpline"
