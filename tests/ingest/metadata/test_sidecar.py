# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json

import nibabel as nib
import numpy as np
import pytest

from halfpipe.ingest.metadata.sidecar import SidecarMetadataLoader
from halfpipe.model.file.base import File


def _epi_fileobj(tmp_path, sidecar: dict) -> File:
    image_path = tmp_path / "sub-01_dir-ap_epi.nii.gz"
    nib.nifti1.Nifti1Image(np.zeros((64, 48, 40, 5)), np.eye(4)).to_filename(image_path)
    (tmp_path / "sub-01_dir-ap_epi.json").write_text(json.dumps(sidecar))
    return File(
        path=str(image_path),
        datatype="fmap",
        suffix="epi",
        extension=".nii.gz",
        tags=dict(sub="01"),
        metadata=dict(),
    )


def test_total_readout_time_used_directly(tmp_path) -> None:
    """A TotalReadoutTime present in the sidecar is used as-is."""
    fileobj = _epi_fileobj(tmp_path, {"PhaseEncodingDirection": "j-", "TotalReadoutTime": 0.0321})

    assert SidecarMetadataLoader().fill(fileobj, "total_readout_time") is True
    assert fileobj.metadata["total_readout_time"] == pytest.approx(0.0321)


def test_total_readout_time_derived_from_effective_echo_spacing(tmp_path) -> None:
    """total_readout_time is derived from EffectiveEchoSpacing and image geometry via sdcflows.get_trt
    when it is not stored directly in the sidecar."""
    fileobj = _epi_fileobj(tmp_path, {"PhaseEncodingDirection": "j-", "EffectiveEchoSpacing": 0.0005})

    assert SidecarMetadataLoader().fill(fileobj, "total_readout_time") is True
    # N_PE along j = shape[1] = 48, so TRT = EffectiveEchoSpacing * (N_PE - 1)
    assert fileobj.metadata["total_readout_time"] == pytest.approx(0.0005 * (48 - 1))


def test_total_readout_time_absent(tmp_path) -> None:
    """When neither TotalReadoutTime nor a derivable spacing is present, the key is left unfilled
    (so downstream collection can drop the field map instead of crashing fMRIPrep)."""
    fileobj = _epi_fileobj(tmp_path, {"PhaseEncodingDirection": "j-"})

    assert SidecarMetadataLoader().fill(fileobj, "total_readout_time") is False
    assert "total_readout_time" not in fileobj.metadata
