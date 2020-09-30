# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Nipype interfaces to calculate connectivity measures using nilearn.
Adapted from https://github.com/Neurita/pypes
"""

import numpy as np
import nibabel as nib

from scipy.ndimage.measurements import mean

from ..utils import nvol


def meansignals(in_file, atlas_file, mask_file=None, background_label=0, min_region_coverage=0.5, output_coverage=False):
    in_img = nib.load(in_file)

    atlas_img = nib.load(atlas_file)
    assert nvol(atlas_img) == 1
    assert atlas_img.shape[:3] == in_img.shape[:3]
    assert np.allclose(atlas_img.affine, in_img.affine)
    labels = np.asanyarray(atlas_img.dataobj).astype(np.int32)

    nlabel = labels.max()

    assert background_label <= nlabel

    indices = np.arange(0, nlabel + 1, dtype=np.int32)

    out_region_coverage = None

    if mask_file is not None:
        mask_img = nib.load(mask_file)
        assert nvol(mask_img) == 1
        assert mask_img.shape[:3] == in_img.shape[:3]
        assert np.allclose(mask_img.affine, in_img.affine)
        mask_data = np.asanyarray(mask_img.dataobj).astype(np.bool)

        pre_counts = np.bincount(np.ravel(labels), minlength=nlabel + 1)
        pre_counts = pre_counts[:nlabel + 1].astype(np.float64)

        labels[np.logical_not(mask_data)] = background_label

        post_counts = np.bincount(np.ravel(labels), minlength=nlabel + 1)
        post_counts = post_counts[:nlabel + 1].astype(np.float64)

        region_coverage = post_counts / pre_counts
        region_coverage[np.isclose(pre_counts, 0)] = 0

        out_region_coverage = list(region_coverage[indices != background_label])
        assert len(out_region_coverage) == nlabel

        indices = indices[region_coverage >= min_region_coverage]

    indices = np.setdiff1d(indices, [background_label])

    assert np.all(labels >= 0)

    in_data = in_img.get_fdata()
    if in_data.ndim == 3:
        in_data = in_data[:, :, :, np.newaxis]
    assert in_data.ndim == 4

    result = np.full((in_data.shape[3], nlabel), np.nan)
    for i, img in enumerate(np.moveaxis(in_data, 3, 0)):
        result[i, indices - 1] = mean(img, labels=labels.reshape(img.shape), index=indices)

    if output_coverage is True:
        return result, out_region_coverage
    else:
        return result
