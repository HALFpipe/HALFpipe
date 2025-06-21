# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from random import seed

import nibabel as nib
import numpy as np
import pytest
from nipype.interfaces import fsl

from halfpipe.interfaces.fslnumpy.regfilt import FilterRegressor
from halfpipe.logging import logger


@pytest.mark.slow
@pytest.mark.timeout(60)
def test_filter_regressor(tmp_path):
    seed(a=0x5E6128C4)

    os.chdir(str(tmp_path))

    array = np.random.rand(10, 10, 10, 100) * 1000 + 10000

    img = nib.nifti1.Nifti1Image(array, np.eye(4))
    assert isinstance(img.header, nib.nifti1.Nifti1Header)
    img.header.set_data_dtype(np.float64)

    in_file = "img.nii.gz"
    nib.loadsave.save(img, in_file)

    x = array.reshape((-1, array.shape[-1]))
    _, _, vh = np.linalg.svd(x, full_matrices=False)
    design = vh[:10, :].T  # first ten pca components
    design_file = "design.txt"
    np.savetxt(design_file, design)

    instance = FilterRegressor()
    instance.inputs.in_file = in_file
    instance.inputs.design_file = design_file
    instance.inputs.filter_columns = [1, 2, 3]
    assert instance.inputs.aggressive is False
    assert instance.inputs.filter_all is False
    assert instance.inputs.mask is True
    result = instance.run()
    assert result.outputs is not None

    r0 = nib.nifti1.load(result.outputs.out_file).get_fdata()

    instance = fsl.FilterRegressor()
    instance.inputs.in_file = in_file
    instance.inputs.design_file = design_file
    instance.inputs.filter_columns = [1, 2, 3]
    result = instance.run()
    assert result.outputs is not None

    r1 = nib.nifti1.load(result.outputs.out_file).get_fdata()

    delta = np.abs(r0 - r1)
    # mean_delta = np.mean(delta, axis=-1)
    maximum_index = np.unravel_index(np.argsort(delta.ravel())[::-1][:3][::-1], delta.shape)
    top_differences = np.column_stack((r0[maximum_index], r1[maximum_index]))
    logger.info(f"Top three differences:\n{top_differences}")
    logger.info(f"Mean absolute difference: {np.mean(delta)}")

    np.testing.assert_allclose(r0, r1, rtol=1e-6, atol=2e-4)
