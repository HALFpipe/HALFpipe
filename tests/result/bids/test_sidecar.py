# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from pathlib import Path
from typing import Any, Mapping
from unittest import TestCase

from halfpipe.result.bids.sidecar import load_sidecar, save_sidecar

sidecar_data: Mapping[str, Any] = {
    "AcquisitionOrientation": "LAS",
    "AcquisitionVolumeShape": [90, 90, 60],
    "AcquisitionVoxelSize": [
        2.4000000953674316,
        2.4000000953674316,
        2.3999998569488525,
    ],
    "DummyScans": 0,
    "EchoTime": 0.03,
    "EffectiveEchoSpacing": 0.000519988,
    "FDMean": 0.15970591562102748,
    "FDPerc": 1.7921146953405016,
    "FallbackRegistration": False,
    "MeanGMTSNR": 50.79828213525886,
    "NumberOfVolumes": 837,
    "PhaseEncodingDirection": "j-",
    "RawSources": [
        "a",
        "b",
        "c",
    ],
    "RepetitionTime": 0.8,
    "ScanStart": 0.0,
    "SdcMethod": "PEB/PEPOLAR (phase-encoding based / PE-POLARity)",
    "Setting": {
        "BandpassFilter": {"HighPassWidth": 125.0, "Type": "gaussian"},
        "GrandMeanScaling": {"Mean": 10000.0},
        "ICAAROMA": False,
        "Smoothing": {"FWHM": 6.0},
    },
    "SliceEncodingDirection": "k",
    "SliceTiming": [
        0.545,
        0.0,
        0.39,
    ],
    "TaskName": "emotionalconflict",
}


def test_sidecar(tmp_path: Path):
    sidecar_path = tmp_path / "sub-0001_task-rest_bold.json"
    with sidecar_path.open("w") as file_handle:
        json.dump(sidecar_data, file_handle, sort_keys=True, indent=4)

    metadata, vals = load_sidecar(sidecar_path)

    save_sidecar(sidecar_path, metadata, vals)

    with sidecar_path.open() as file_handle:
        saved_data = json.load(file_handle)

    TestCase().assertDictEqual(sidecar_data, saved_data)
