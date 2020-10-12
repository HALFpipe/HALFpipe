# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import numpy as np

import nibabel as nib

from halfpipe.model import File
from halfpipe.io.metadata.niftimetadata import NiftiheaderMetadataLoader


def test_NiftiheaderMetadataLoader_3d_zooms(tmp_path):
    size = (2, 3, 4)

    fname = str(tmp_path / "test.nii")

    nib.Nifti1Image(np.zeros(size), np.eye(4)).to_filename(fname)

    fileobj = File(path=fname, datatype="anat", metadata=dict())

    loader = NiftiheaderMetadataLoader()

    assert loader.fill(fileobj, "repetition_time") is False
    assert "repetition_time" not in fileobj.metadata
