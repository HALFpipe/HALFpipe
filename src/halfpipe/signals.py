# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Literal, overload

import nibabel as nib
import numpy as np
import scipy
from numpy import typing as npt

from .utils.image import nvol
from .utils.matrix import atleast_4d


@overload
def mean_signals(
    data_image: nib.analyze.AnalyzeImage,
    atlas_image: nib.analyze.AnalyzeImage,
    output_coverage: Literal[False] = False,
    mask_image: nib.analyze.AnalyzeImage | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
) -> npt.NDArray: ...


@overload
def mean_signals(
    data_image: nib.analyze.AnalyzeImage,
    atlas_image: nib.analyze.AnalyzeImage,
    output_coverage: Literal[True],
    mask_image: nib.analyze.AnalyzeImage | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
) -> tuple[npt.NDArray, list[float]]: ...


def mean_signals(
    data_image: nib.analyze.AnalyzeImage,
    atlas_image: nib.analyze.AnalyzeImage,
    output_coverage: bool = False,
    mask_image: nib.analyze.AnalyzeImage | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
):
    volume_shape = data_image.shape[:3]
    if atlas_image.shape[:3] != volume_shape:
        raise ValueError("Atlas image and data image must have the same shape")
    if not np.allclose(atlas_image.affine, data_image.affine):
        raise ValueError("Atlas image and data image must have the same affine")

    atlas_volumes = atleast_4d(np.asanyarray(atlas_image.dataobj).astype(int))
    label_count: int = atlas_volumes.max()

    if background_label > label_count:
        raise ValueError(f"Background label {background_label} was not found in atlas")

    data: npt.NDArray[np.float64] = atleast_4d(data_image.get_fdata())
    mask: npt.NDArray[np.bool_] = np.ones(volume_shape, dtype=bool)

    volume_count = data.shape[3]
    signals = np.full((volume_count, label_count), np.nan)
    region_coverage_array: npt.NDArray[np.float64] = np.full(label_count + 1, np.nan)

    seen_labels: set[int] = set()

    if mask_image is not None:
        if nvol(mask_image) != 1:
            raise ValueError("Mask image cannot be a 4D image")
        if mask_image.shape[:3] != data_image.shape[:3]:
            raise ValueError("Mask image and data image must have the same shape")
        if not np.allclose(mask_image.affine, data_image.affine):
            raise ValueError("Mask image and data image must have the same affine")
        mask_image = nib.funcs.squeeze_image(mask_image)  # Remove trailing singleton dimensions.
        if mask_image is None:
            raise RuntimeError("Failed to squeeze mask image")
        mask = np.asanyarray(mask_image.dataobj).astype(bool)

    for atlas_volume in np.moveaxis(atlas_volumes, 3, 0):
        labels = np.arange(0, label_count + 1, dtype=int)

        if not np.all(mask):
            unmasked_counts = np.bincount(np.ravel(atlas_volume), minlength=label_count + 1)
            unmasked_counts = unmasked_counts[: label_count + 1]

            atlas_volume[np.logical_not(mask)] = background_label
            masked_counts = np.bincount(np.ravel(atlas_volume), minlength=label_count + 1)
            masked_counts = masked_counts[: label_count + 1]

            has_voxels = unmasked_counts != 0
            region_coverage = np.zeros(label_count + 1)
            region_coverage[has_voxels] = masked_counts[has_voxels] / unmasked_counts[has_voxels]

            region_coverage_array[has_voxels] = region_coverage[has_voxels]

            has_coverage = region_coverage >= min_region_coverage
            labels = labels[has_voxels & has_coverage]

        labels = labels[labels != background_label]

        if np.any(labels < 0):
            raise ValueError("Atlas image contains negative values")
        if set(labels) & seen_labels:
            raise ValueError("Atlas image contains duplicate labels across volumes")
        seen_labels |= set(labels)

        for j, data_volume in enumerate(np.moveaxis(data, 3, 0)):
            signals[j, labels - 1] = scipy.ndimage.mean(
                data_volume,
                labels=atlas_volume.reshape(data_volume.shape),
                index=labels,
            )

    if output_coverage is True:
        labels = np.arange(0, label_count + 1, dtype=int)
        labels = labels[labels != background_label]
        return signals, list(region_coverage_array[labels])
    else:
        return signals


@overload
def mode_signals(
    cope_img: nib.analyze.AnalyzeImage,
    var_cope_img: nib.analyze.AnalyzeImage,
    modes_img: nib.analyze.AnalyzeImage,
    output_coverage: Literal[False] = False,
) -> npt.NDArray: ...


@overload
def mode_signals(
    cope_img: nib.analyze.AnalyzeImage,
    var_cope_img: nib.analyze.AnalyzeImage,
    modes_img: nib.analyze.AnalyzeImage,
    output_coverage: Literal[True],
) -> tuple[npt.NDArray, npt.NDArray]: ...


def mode_signals(
    cope_img: nib.analyze.AnalyzeImage,
    var_cope_img: nib.analyze.AnalyzeImage,
    modes_img: nib.analyze.AnalyzeImage,
    output_coverage: bool = False,
) -> npt.NDArray | tuple[npt.NDArray, npt.NDArray]:
    """
    Compute the mode signals for a given set of cope, varcope, and modes images.

    Parameters
    ----------
    cope_img : nib.analyze.AnalyzeImage
        The cope image.
    var_cope_img : nib.analyze.AnalyzeImage
        The varcope image.
    modes_img : nib.analyze.AnalyzeImage
        The modes image.
    output_coverage : bool, optional
        Whether to output the coverage, by default False.

    Returns
    -------
    npt.NDArray | tuple[npt.NDArray, npt.NDArray]
        The mode signals, and optionally the coverage.

    Raises
    ------
    ValueError
        If the input images do not have the same shape.
    """
    if modes_img.shape[:3] != cope_img.shape[:3]:
        raise ValueError("Atlas image and input image must have the same volume shape.")
    if cope_img.shape[:3] != var_cope_img.shape[:3]:
        raise ValueError("Cope image and varcope image must have the same shape.")
    if not np.allclose(modes_img.affine, cope_img.affine):
        raise ValueError("Atlas image and input image must have the same affine.")

    # Load the data.
    cope_data = cope_img.get_fdata()

    var_cope_data = var_cope_img.get_fdata()
    if np.isnan(var_cope_data).all():  # No varcope data, so assume equal weights.
        var_cope_data[:] = 1

    modes_data = modes_img.get_fdata()
    voxel_sum = modes_data.sum(axis=(0, 1, 2))

    mask_data = np.isfinite(cope_data) & np.isfinite(var_cope_data)

    # Remove voxels with no data.
    maximum_mask = mask_data.any(axis=3)
    cope_data = cope_data[maximum_mask, :]
    var_cope_data = var_cope_data[maximum_mask, :]
    modes_data = modes_data[maximum_mask, :]
    mask_data = mask_data[maximum_mask, :]

    # Create the output arrays.
    mode_count = modes_data.shape[-1]
    volume_count = cope_data.shape[-1]
    signals_lstsq = np.full((volume_count, mode_count), np.nan)
    coverage = np.full((volume_count, mode_count), np.nan)

    for i in range(volume_count):
        mask = mask_data[:, i]

        masked_mode_data = modes_data[mask, :]
        masked_voxel_sum = masked_mode_data.sum(axis=0)
        coverage[i, :] = masked_voxel_sum / voxel_sum

        # Reciprocal of the square root.
        weights = np.power(var_cope_data[mask, i, np.newaxis], -0.5)

        # Prepare the weighted variables.
        weighted_endog = cope_data[mask, i, np.newaxis] * weights
        weighted_exog = masked_mode_data * weights

        gram_matrix = weighted_exog.transpose() @ weighted_exog
        correlation_vector = weighted_exog.transpose() @ weighted_endog

        signals_lstsq[i, :, np.newaxis], _, _, _ = scipy.linalg.lstsq(
            gram_matrix,
            correlation_vector,
            check_finite=False,
            lapack_driver="gelsy",
            overwrite_a=True,
            overwrite_b=True,
        )

    if output_coverage is True:
        return signals_lstsq, coverage
    else:
        return signals_lstsq
