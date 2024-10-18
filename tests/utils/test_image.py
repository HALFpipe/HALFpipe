# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os

import pytest
from nibabel.testing import data_path

from halfpipe.utils.image import nifti_dim, nvol


@pytest.fixture
def example_nifti():
    return os.path.join(str(data_path), "example4d.nii.gz")


def test_image_nifti_dim(example_nifti):
    assert nifti_dim(example_nifti, 0) == 128


def test_image_nvol(example_nifti):
    assert nvol(example_nifti) == 2
