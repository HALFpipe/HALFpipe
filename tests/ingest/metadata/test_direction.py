# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import nibabel as nib
import numpy as np
from halfpipe.ingest.metadata.direction import get_axcodes_set
from halfpipe.resource import get as get_resource

from ...resource import setup as setup_test_resources


def test_get_axcodes_set_bad_qform() -> None:
    """
    Regression test for the `get_axcodes_set` function.
    Makes sure that bad qform information in image headers
     does not break the program. Original error was
    `ValueError: w2 should be positive, but is -9.483971e-07`
    """
    setup_test_resources()
    path = get_resource("bad_quaternion.nii.gz")
    get_axcodes_set(path)


def test_get_axcodes_set_bad_dim(tmp_path: Path) -> None:
    qform = np.array(
        [
            [-3.40613774e00, 1.20595035e-02, -3.09338179e-02, 1.08900032e02],
            [1.41020389e-02, 3.39867230e00, -2.26973045e-01, -8.02476349e01],
            [-3.01166839e-02, 2.27511077e-01, 3.39227460e00, -5.93646622e01],
            [0.00000000e00, 0.00000000e00, 0.00000000e00, 1.00000000e00],
        ]
    )
    image = nib.nifti1.Nifti1Image(np.zeros((64, 64, 12167)), qform)

    sform = np.array(
        [
            [-3.40572619e00, 8.95179156e-03, -0.00000000e00, 1.08900032e02],
            [1.71206165e-02, 3.37589908e00, 0.00000000e00, -8.02476349e01],
            [-6.01542667e-02, 4.53988314e-01, 0.00000000e00, -5.93646622e01],
            [0.00000000e00, 0.00000000e00, 0.00000000e00, 1.00000000e00],
        ]
    )
    image.header.set_sform(sform)

    image_path = tmp_path / "bad_dim.nii.gz"
    nib.save(image, image_path)

    assert get_axcodes_set(image_path) == {("L", "A", "S")}
