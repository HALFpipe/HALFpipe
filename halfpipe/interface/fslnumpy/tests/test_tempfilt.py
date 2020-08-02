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

from halfpipe.interface import TemporalFilter
from nipype.interfaces import fsl


def test_TemporalFilter():
    seed(a=0x4d3c732f)

    array = np.random.rand(10, 10, 10, 100) * 1000 + 10000
    img = nib.Nifti1Image(array, np.eye(4))

    temp_dir = Path(mkdtemp(prefix="test_TemporalFilter_"))
    cur_dir = os.getcwd()
    os.chdir(temp_dir)

    in_file = "img.nii.gz"
    nib.save(img, in_file)

    instance = TemporalFilter()
    instance.inputs.in_file = in_file
    instance.inputs.lowpass_sigma = 12
    instance.inputs.highpass_sigma = 125
    result = instance.run()

    r0 = nib.load(result.outputs.out_file).get_fdata()

    instance = fsl.TemporalFilter()
    instance.inputs.in_file = in_file
    instance.inputs.lowpass_sigma = 12
    instance.inputs.highpass_sigma = 125
    result = instance.run()

    r1 = nib.load(result.outputs.out_file).get_fdata()

    os.chdir(cur_dir)
    rmtree(temp_dir)

    assert np.allclose(r0, r1)
