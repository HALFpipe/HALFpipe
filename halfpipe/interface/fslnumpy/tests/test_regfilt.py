# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""
from tempfile import mkdtemp
from shutil import rmtree
from pathlib import Path
import os
from random import seed

import nibabel as nib
import numpy as np

from halfpipe.interface import FilterRegressor
from nipype.interfaces import fsl


def test_FilterRegressor():
    seed(a=0x5e6128c4)

    temp_dir = Path(mkdtemp(prefix="test_FilterRegressor_"))
    cur_dir = os.getcwd()
    os.chdir(temp_dir)

    array = np.random.rand(10, 10, 10, 100) * 1000 + 10000

    img = nib.Nifti1Image(array, np.eye(4))
    in_file = "img.nii.gz"
    nib.save(img, in_file)

    x = array.reshape((-1, array.shape[-1]))
    u, s, vh = np.linalg.svd(x, full_matrices=False)
    design = vh[:10, :].T  # first ten pca components
    design_file = "design.txt"
    np.savetxt(design_file, design)

    instance = FilterRegressor()
    instance.inputs.in_file = in_file
    instance.inputs.design_file = design_file
    instance.inputs.filter_columns = [1, 2, 3]
    result = instance.run()

    r0 = nib.load(result.outputs.out_file).get_fdata()

    instance = fsl.FilterRegressor()
    instance.inputs.in_file = in_file
    instance.inputs.design_file = design_file
    instance.inputs.filter_columns = [1, 2, 3]
    result = instance.run()

    r1 = nib.load(result.outputs.out_file).get_fdata()

    os.chdir(cur_dir)
    rmtree(temp_dir)

    print(np.mean(np.abs(r0 - r1)))
    assert np.allclose(r0, r1)
