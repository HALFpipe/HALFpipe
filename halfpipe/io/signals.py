# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
Nipype interfaces to calculate connectivity measures using nilearn.
Adapted from https://github.com/Neurita/pypes
"""

from typing import List, Optional, Union, overload, Tuple
from typing_extensions import Literal

from pathlib import Path

import numpy as np
import nibabel as nib

from scipy.ndimage.measurements import mean

from ..utils import nvol, atleast_4d


@overload
def mean_signals(
    in_file: Union[str, Path],
    atlas_file: Union[str, Path],
    mask_file: Optional[Union[str, Path]] = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
    output_coverage: Literal[False] = False,
) -> np.ndarray:
    ...


@overload
def mean_signals(
    in_file: Union[str, Path],
    atlas_file: Union[str, Path],
    mask_file: Optional[Union[str, Path]] = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
    output_coverage: Literal[True] = True,
) -> Tuple[np.ndarray, List[float]]:
    ...


def mean_signals(
    in_file: Union[str, Path],
    atlas_file: Union[str, Path],
    mask_file: Optional[Union[str, Path]] = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
    output_coverage: bool = False,
):
    in_img = nib.load(in_file)
    atlas_img = nib.load(atlas_file)

    assert nvol(atlas_img) == 1
    assert atlas_img.shape[:3] == in_img.shape[:3]
    assert np.allclose(atlas_img.affine, in_img.affine)

    labels = np.asanyarray(atlas_img.dataobj).astype(int)

    nlabel: int = labels.max()

    assert background_label <= nlabel

    indices = np.arange(0, nlabel + 1, dtype=int)

    out_region_coverage = None

    if mask_file is not None:
        mask_img = nib.load(mask_file)

        assert nvol(mask_img) == 1
        assert mask_img.shape[:3] == in_img.shape[:3]
        assert np.allclose(mask_img.affine, in_img.affine)

        mask_data = np.asanyarray(mask_img.dataobj).astype(bool)

        unmasked_counts = np.bincount(
            np.ravel(labels), minlength=nlabel + 1
        )[:nlabel + 1]

        labels[np.logical_not(mask_data)] = background_label

        masked_counts = np.bincount(
            np.ravel(labels), minlength=nlabel + 1
        )[:nlabel + 1]

        region_coverage = masked_counts.astype(float) / unmasked_counts.astype(float)
        region_coverage[unmasked_counts == 0] = 0

        out_region_coverage = list(region_coverage[indices != background_label])
        assert len(out_region_coverage) == nlabel

        indices = indices[region_coverage >= min_region_coverage]

    indices = indices[indices != background_label]

    assert np.all(labels >= 0)

    in_data = atleast_4d(in_img.get_fdata())

    result = np.full((in_data.shape[3], nlabel), np.nan)

    for i, img in enumerate(np.moveaxis(in_data, 3, 0)):
        result[i, indices - 1] = mean(
            img, labels=labels.reshape(img.shape), index=indices
        )

    if output_coverage is True:
        return result, out_region_coverage
    else:
        return result
