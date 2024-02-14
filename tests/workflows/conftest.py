# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from zipfile import ZipFile

import nibabel as nib
import pytest
from halfpipe.resource import get as get_resource
from nilearn.image import new_img_like

from ..resource import setup as setup_test_resources


@pytest.fixture(scope="package")
def bids_data(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="bids_data")

    os.chdir(str(tmp_path))

    setup_test_resources()
    input_path = get_resource("bids_data.zip")

    with ZipFile(input_path) as fp:
        fp.extractall(tmp_path)

    bids_data_path = tmp_path / "bids_data"

    func_path = bids_data_path / "sub-1012" / "func"

    Path(func_path / "sub-1012_task-rest_events.tsv").unlink()  # this file is empty

    bold_file = func_path / "sub-1012_task-rest_bold.nii.gz"
    bold_img = nib.nifti1.load(bold_file)
    bold_data = bold_img.get_fdata()[..., :64]  # we don't need so many volumes for testing
    bold_img = new_img_like(bold_img, bold_data, copy_header=True)
    nib.loadsave.save(bold_img, bold_file)

    return bids_data_path
