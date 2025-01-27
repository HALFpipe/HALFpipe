# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from random import seed

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from halfpipe.ingest.spreadsheet import read_spreadsheet
from halfpipe.interfaces.utility.remove_volumes import RemoveVolumes
from halfpipe.resource import get as get_resource

from ...resource import setup as setup_test_resources


@pytest.mark.parametrize("header", [True, False])
def test_remove_volumes_tsv(tmp_path, header):
    seed(a=0x5E6128C4)

    m = 100
    n = 5

    skip_vols = 3

    column_names = [f"column_{i + 1}" for i in range(n)]

    data_frame = pd.DataFrame(np.random.rand(m, n), columns=column_names)

    data_file = tmp_path / "data.tsv"
    data_frame.to_csv(data_file, sep="\t", header=header, index=False)

    remove_volumes = RemoveVolumes(in_file=data_file, skip_vols=skip_vols, write_header=header)

    cwd = tmp_path / "remove_volumes"
    cwd.mkdir()

    result = remove_volumes.run(cwd=cwd)
    assert result.outputs is not None

    test_data_frame = read_spreadsheet(result.outputs.out_file)
    assert np.allclose(test_data_frame.values, data_frame.values[skip_vols:, :])


def test_remove_volumes_nii(tmp_path):
    setup_test_resources()

    data_file = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")

    skip_vols = 3

    remove_volumes = RemoveVolumes(in_file=data_file, skip_vols=skip_vols)

    cwd = tmp_path / "remove_volumes"
    cwd.mkdir()

    result = remove_volumes.run(cwd=cwd)
    assert result.outputs is not None

    image = nib.nifti1.load(data_file)
    test_image = nib.nifti1.load(result.outputs.out_file)
    assert np.allclose(test_image.get_fdata(), image.get_fdata()[..., skip_vols:])
