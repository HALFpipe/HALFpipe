# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import pytest
import numpy as np
import nibabel as nib

from ....model import File
from ..niftimetadata import NiftiheaderMetadataLoader


@pytest.mark.timeout(60)
def test_NiftiheaderMetadataLoader_repetition_time_3d(tmp_path):
    size = (2, 3, 4)

    fname = str(tmp_path / "test.nii")

    nib.Nifti1Image(np.zeros(size), np.eye(4)).to_filename(fname)

    fileobj = File(path=fname, datatype="anat", metadata=dict())

    loader = NiftiheaderMetadataLoader(None)

    assert loader.fill(fileobj, "repetition_time") is False
    assert "repetition_time" not in fileobj.metadata


@pytest.mark.timeout(60)
@pytest.mark.parametrize("units", ["msec", "usec", "sec", "unknown"])
def test_NiftiheaderMetadataLoader_repetition_time_units(tmp_path, units):
    size = (1, 2, 3, 4)
    repetition_time = 1.234  # seconds

    fname = str(tmp_path / "test.nii")

    img = nib.Nifti1Image(np.zeros(size), np.eye(4))

    zooms = [1.0, 1.0, 1.0, repetition_time]

    if units == "msec":
        zooms[3] *= 1e3
    elif units == "usec":
        zooms[3] *= 1e6

    img.header.set_zooms(zooms)
    img.header.set_xyzt_units(t=units)

    img.to_filename(fname)

    fileobj = File(path=fname, datatype="func", metadata=dict())

    loader = NiftiheaderMetadataLoader(None)

    assert loader.fill(fileobj, "repetition_time") is True
    assert "repetition_time" in fileobj.metadata
    assert np.isclose(fileobj.metadata["repetition_time"], repetition_time)
