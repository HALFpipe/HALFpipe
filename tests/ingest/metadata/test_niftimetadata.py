# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nibabel as nib
import numpy as np
import pytest

from halfpipe.ingest.metadata.niftimetadata import NiftiheaderMetadataLoader
from halfpipe.model.file.base import File


class MockLoader:
    def fill(self, fileobj, key):
        return True


def test_nifti_header_metadata_loader_repetition_time_3d(tmp_path):
    size = (2, 3, 4)

    fname = str(tmp_path / "test.nii")

    nib.nifti1.Nifti1Image(np.zeros(size), np.eye(4)).to_filename(fname)

    fileobj = File(path=fname, datatype="anat", metadata=dict())

    loader = NiftiheaderMetadataLoader(None)

    assert loader.fill(fileobj, "repetition_time") is False
    assert "repetition_time" not in fileobj.metadata


@pytest.mark.parametrize("units", ["msec", "usec", "sec", "unknown"])
def test_nifti_header_metadata_loader_repetition_time_units(tmp_path, units):
    size = (1, 2, 3, 4)
    repetition_time = 1.234  # seconds

    fname = str(tmp_path / "test.nii")

    img = nib.nifti1.Nifti1Image(np.zeros(size), np.eye(4))
    assert isinstance(img.header, nib.nifti1.Nifti1Header)

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


@pytest.mark.parametrize("nifti_slice_duration", [0.0, 42, 70])
def test_nifti_header_metadata_loader_slice_timing(tmp_path, nifti_slice_duration):
    size = (10, 10, 60, 125)
    repetition_time = 2.5  # seconds

    fname = str(tmp_path / "test.nii")

    img = nib.nifti1.Nifti1Image(np.zeros(size), np.eye(4))
    assert isinstance(img.header, nib.nifti1.Nifti1Header)

    zooms = [1.0, 1.0, 1.0, repetition_time]

    img.header.set_zooms(zooms)
    img.header.set_dim_info(slice=2)
    img.header.set_slice_duration(nifti_slice_duration)

    img.to_filename(fname)

    fileobj = File(
        path=fname,
        datatype="func",
        metadata=dict(
            slice_encoding_direction="k",
            slice_timing_code="sequential increasing",
        ),
    )

    loader = NiftiheaderMetadataLoader(MockLoader())

    assert loader.fill(fileobj, "repetition_time") is True
    assert loader.fill(fileobj, "slice_timing") is True
    assert max(fileobj.metadata["slice_timing"]) < repetition_time
