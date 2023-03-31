# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Literal, overload

import nibabel as nib
import numpy as np
import scipy
from numpy import typing as npt
from tqdm.auto import tqdm

from .utils.image import nvol
from .utils.matrix import atleast_4d


@overload
def mean_signals(
    in_img: nib.Nifti1Image,
    atlas_img: nib.Nifti1Image,
    output_coverage: Literal[False] = False,
    mask_img: nib.Nifti1Image | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
) -> npt.NDArray:
    ...


@overload
def mean_signals(
    in_img: nib.Nifti1Image,
    atlas_img: nib.Nifti1Image,
    output_coverage: Literal[True],
    mask_img: nib.Nifti1Image | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
) -> tuple[npt.NDArray, list[float]]:
    ...


def mean_signals(
    in_img: nib.Nifti1Image,
    atlas_img: nib.Nifti1Image,
    output_coverage: bool = False,
    mask_img: nib.Nifti1Image | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
):
    if nvol(atlas_img) != 1:
        raise ValueError("Atlas image cannot be a 4D image.")
    volume_shape = in_img.shape[:3]
    if atlas_img.shape[:3] != volume_shape:
        raise ValueError("Atlas image and input image must have the same shape.")
    if not np.allclose(atlas_img.affine, in_img.affine):
        raise ValueError("Atlas image and input image must have the same affine.")

    labels = np.asanyarray(atlas_img.dataobj).astype(int)
    label_count: int = labels.max()

    if background_label > label_count:
        raise ValueError(f"Background label {background_label} was not found in atlas.")

    indices = np.arange(0, label_count + 1, dtype=int)
    region_coverage_list: list[float] | None = None

    in_data = atleast_4d(in_img.get_fdata())
    mask_data = np.ones(volume_shape, dtype=bool)
    if mask_img is not None:
        if nvol(mask_img) != 1:
            raise ValueError("Mask image cannot be a 4D image.")
        if mask_img.shape[:3] != in_img.shape[:3]:
            raise ValueError("Mask image and input image must have the same shape.")
        if not np.allclose(mask_img.affine, in_img.affine):
            raise ValueError("Mask image and input image must have the same affine.")
        mask_data = np.asanyarray(mask_img.dataobj).astype(bool)

    if not np.all(mask_data):
        unmasked_counts = np.bincount(np.ravel(labels), minlength=label_count + 1)
        unmasked_counts = unmasked_counts[: label_count + 1]

        labels[np.logical_not(mask_data)] = background_label
        masked_counts = np.bincount(np.ravel(labels), minlength=label_count + 1)
        masked_counts = masked_counts[: label_count + 1]

        region_coverage = masked_counts.astype(float) / unmasked_counts.astype(float)
        region_coverage[unmasked_counts == 0] = 0

        region_coverage_list = list(region_coverage[indices != background_label])
        if len(region_coverage_list) != label_count:
            raise RuntimeError("Unexpected number of covarage values.")

        indices = indices[region_coverage >= min_region_coverage]

    indices = indices[indices != background_label]

    if np.any(labels < 0):
        raise ValueError("Atlas image contains negative values.")

    volume_count = in_data.shape[3]
    signals = np.full((volume_count, label_count), np.nan)

    for i, img in enumerate(np.moveaxis(in_data, 3, 0)):
        signals[i, indices - 1] = scipy.ndimage.mean(
            img, labels=labels.reshape(img.shape), index=indices
        )

    if output_coverage is True:
        return signals, region_coverage_list
    else:
        return signals


def mode_signals(
    cope_img: nib.Nifti1Image,
    var_cope_img: nib.Nifti1Image,
    modes_img: nib.Nifti1Image,
) -> npt.NDArray:
    if modes_img.shape[:3] != cope_img.shape[:3]:
        raise ValueError("Atlas image and input image must have the same volume shape.")
    if cope_img.shape[:3] != var_cope_img.shape[:3]:
        raise ValueError("Cope image and varcope image must have the same shape.")
    if not np.allclose(modes_img.affine, cope_img.affine):
        raise ValueError("Atlas image and input image must have the same affine.")

    cope_data = cope_img.get_fdata()

    var_cope_data = var_cope_img.get_fdata()
    if np.isnan(var_cope_data).all():  # No varcope data.
        var_cope_data[:] = 1

    modes_data = modes_img.get_fdata()

    mode_count = modes_data.shape[3]
    volume_count = cope_data.shape[3]
    signals_lstsq = np.full((volume_count, mode_count), np.nan)

    for i in tqdm(range(volume_count), desc="extracting signals", leave=False):
        cope = cope_data[..., i]
        var_cope = var_cope_data[..., i]

        mask = np.isfinite(cope) & np.isfinite(var_cope)
        cope = cope[mask]
        var_cope = var_cope[mask]
        modes = modes_data[mask, :]

        weights = np.power(var_cope, -0.5)  # Reciprocal of the square root.
        wendog = cope * weights
        wexog = modes * weights[:, np.newaxis]

        signals_lstsq[i, :], _, _, _ = scipy.linalg.lstsq(
            wexog,
            wendog,
            check_finite=False,
            lapack_driver="gelsy",
            overwrite_a=True,
            overwrite_b=True,
        )

    return signals_lstsq

    # signals = np.full((volume_count, mode_count), np.nan)

    # mask = np.isfinite(cope_data) & np.isfinite(var_cope_data)
    # maximum_mask = mask.any(axis=3)

    # cope_data = cope_data[maximum_mask, :]
    # var_cope_data = var_cope_data[maximum_mask, :]
    # modes_data = modes_data[maximum_mask, :]

    # mask = np.isfinite(cope_data) & np.isfinite(var_cope_data)
    # minimum_mask = mask.all(axis=1)
    # (minimum_indices,) = np.where(minimum_mask)
    # minimum_q, minimum_r = np.linalg.qr(modes_data[minimum_mask, :])

    # for i in tqdm(range(volume_count), desc="extracting signals", leave=False):
    #     cope = cope_data[..., i]
    #     var_cope = var_cope_data[..., i]

    #     mask = np.isfinite(cope) & np.isfinite(var_cope)
    #     difference_mask = mask & ~minimum_mask
    #     (difference_indices,) = np.where(difference_mask)

    #     indices = np.concatenate((minimum_indices, difference_indices))

    #     difference_q, difference_r = np.linalg.qr(modes_data[difference_mask, :])

    #     stacked_r = np.concatenate((minimum_r, difference_r), axis=0)
    #     q_2, r = np.linalg.qr(stacked_r)
    #     left_singular_vectors, singular_values, right_singular_vectors = np.linalg.svd(
    #         r, full_matrices=False
    #     )

    #     minimum_q_2 = q_2[:mode_count, :]
    #     difference_q_2 = q_2[mode_count:, :]
    #     q = np.concatenate(
    #         (minimum_q @ minimum_q_2, difference_q @ difference_q_2), axis=0
    #     )
    #     left_singular_vectors = q @ left_singular_vectors

    #     cope = cope[indices]
    #     var_cope = var_cope[indices]
    #     modes = modes_data[indices, :]
    #     weights = np.power(var_cope, -0.5)  # Reciprocal of the square root.
    #     wendog = cope * weights
    #     wexog = modes * weights[:, np.newaxis]

    #     wexog_pinv_ = pinv(
    #         q @ left_singular_vectors,
    #         singular_values,
    #         right_singular_vectors,
    #     )

    #     import pdb

    #     pdb.set_trace()

    # return signals
