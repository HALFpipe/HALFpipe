# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import os

import nibabel as nib
import numpy as np
from nilearn.image import new_img_like
from templateflow import api

from ..transformer import Transformer


def test_transformer_nii(tmp_path):
    os.chdir(str(tmp_path))

    api_args = dict(template="MNI152NLin2009cAsym", resolution=2)
    ref_mask_file = api.get(**api_args, desc="brain", suffix="mask")
    ref_mask_img = nib.load(ref_mask_file)

    ref_mask = ref_mask_img.get_fdata() > 0
    n_voxels = np.count_nonzero(ref_mask)
    n_volumes = 10

    test_array = np.random.rand(n_voxels, n_volumes)
    test_img_data = np.zeros((*ref_mask_img.shape, n_volumes), dtype=float)
    test_img_data[ref_mask, :] = test_array

    img = new_img_like(ref_mask_img, test_img_data, copy_header=True)
    img.header.set_data_dtype(np.float64)
    test_file = "img.nii.gz"
    nib.save(img, test_file)

    tf = Transformer()
    tf.inputs.mask = ref_mask_file

    array = tf._load(test_file)

    out_file = tf._dump(array)

    img_data = nib.load(out_file).get_fdata()

    assert np.allclose(test_img_data, img_data)
