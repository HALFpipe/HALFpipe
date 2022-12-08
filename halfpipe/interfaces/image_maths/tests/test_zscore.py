# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from math import isclose

import nibabel as nib
import numpy as np
from nilearn.image import new_img_like
from templateflow import api

from ..zscore import ZScore

abs_tol = 1e-10


def test_zscore(tmp_path):
    os.chdir(str(tmp_path))

    api_args = dict(template="MNI152NLin2009cAsym", resolution=2)
    ref_mask_file = api.get(**api_args, desc="brain", suffix="mask")
    ref_mask_img = nib.load(ref_mask_file)

    ref_mask = ref_mask_img.get_fdata() > 0
    n_voxels = np.count_nonzero(ref_mask)

    test_data = np.random.rand(n_voxels)
    assert not isclose(np.mean(test_data), 0, abs_tol=abs_tol)
    assert not isclose(np.std(test_data), 1, abs_tol=abs_tol)

    test_img_data = np.zeros(ref_mask_img.shape, dtype=float)
    test_img_data[ref_mask] = test_data

    img = new_img_like(ref_mask_img, test_img_data, copy_header=True)
    assert isinstance(img.header, nib.Nifti1Header)
    img.header.set_data_dtype(np.float64)
    test_file = "img.nii.gz"
    nib.save(img, test_file)

    instance = ZScore()
    instance.inputs.in_file = test_file
    instance.inputs.mask = ref_mask_file

    result = instance.run()
    assert result.outputs is not None

    out_img = nib.load(result.outputs.out_file)
    out_img_data = out_img.get_fdata()
    out_data = out_img_data[ref_mask]

    assert isclose(np.mean(out_data), 0, abs_tol=abs_tol)
    assert isclose(np.std(out_data), 1, abs_tol=abs_tol)
