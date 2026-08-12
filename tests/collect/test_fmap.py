# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import pytest

from halfpipe.collect.fmap import PhaseEncodingDirection, check_opposing_pe, collect_fieldmaps
from halfpipe.ingest.database import Database
from halfpipe.ingest.resolve import ResolvedSpec
from halfpipe.model.file.base import File
from halfpipe.model.spec import Spec

bold_file_path = "bold.nii.gz"


def mock_bold_file(
    metadata_phase_encoding_direction: str | None = None,
    dir: str | None = None,
    path: str = bold_file_path,
    tags: dict[str, str] | None = None,
) -> File:
    file_tags = dict(sub="01")
    if tags is not None:
        file_tags.update(tags)
    if dir is not None:
        file_tags["dir"] = dir
    metadata = dict()
    if metadata_phase_encoding_direction is not None:
        metadata["phase_encoding_direction"] = metadata_phase_encoding_direction
    return File(
        path=path,
        datatype="func",
        suffix="bold",
        extension=".nii.gz",
        tags=file_tags,
        metadata=metadata,
    )


def mock_fmap_file(
    suffix: str,
    metadata: dict | None = None,
    path: str | None = None,
    tags: dict[str, str] | None = None,
    intended_for: dict[str, list[str]] | None = None,
) -> File:
    file_tags = dict(sub="01")
    if tags is not None:
        file_tags.update(tags)
    if path is None:
        path = suffix + ".nii.gz"
    fmap = File(
        path=path,
        datatype="fmap",
        suffix=suffix,
        extension=".nii.gz",
        tags=file_tags,
        # Copy so shared parametrization dicts are never mutated
        metadata=dict(metadata) if metadata is not None else dict(),
    )
    fmap.intended_for = intended_for
    return fmap


@pytest.mark.parametrize(
    "pe_dir,axis,sign",
    [
        ("j", "j", "+"),
        ("j-", "j", "-"),
        ("i+", "i", "+"),
        ("k", "k", "+"),
    ],
)
def test_phase_encoding_direction(pe_dir: str, axis: str, sign: str) -> None:
    pe_dir = PhaseEncodingDirection(pe_dir)
    assert pe_dir.axis == axis
    assert pe_dir.sign == sign


def test_empty_phase_encoding_direction() -> None:
    with pytest.raises(ValueError):
        _ = PhaseEncodingDirection("").axis


def test_check_opposing_pe() -> None:
    j = PhaseEncodingDirection("j")

    def mock_epi_fmaps(*pe_dirs: str) -> list[tuple[str, PhaseEncodingDirection]]:
        return [(f"fmap{i}.nii.gz", PhaseEncodingDirection(pe_dir)) for i, pe_dir in enumerate(pe_dirs)]

    # (has_opposing_pe, has_same_axis)
    assert check_opposing_pe(mock_epi_fmaps("j", "j-"), j) == (True, True)  # opposing pair on the BOLD axis
    assert check_opposing_pe(mock_epi_fmaps("j"), j) == (False, True)  # same axis, same sign
    assert check_opposing_pe(mock_epi_fmaps("i", "i-"), j) == (False, False)  # different axis only
    assert check_opposing_pe([], j) == (False, False)  # no field maps on the BOLD axis


@pytest.mark.parametrize(
    "bold_pe_dir, epi_pe_dirs, total_readout_time, expected",
    [
        pytest.param(
            "j",
            {"ap.nii.gz": "j", "pa.nii.gz": "j-"},
            0.05,
            ["ap.nii.gz", "pa.nii.gz"],
            id="opposing-pair",
        ),
        pytest.param(
            "j",
            {"ap.nii.gz": "j", "pa.nii.gz": "j"},
            0.05,
            [],
            id="same-direction",
        ),
        pytest.param(
            "j",
            {"i.nii.gz": "i", "i-.nii.gz": "i-"},
            0.05,
            [],
            id="different-axis",
        ),
        pytest.param(
            "j",
            {"ap.nii.gz": "j", "pa.nii.gz": "j-", "lr.nii.gz": "i"},
            0.05,
            ["ap.nii.gz", "pa.nii.gz"],
            id="opposing-pair-and-different-axis",
        ),
        pytest.param(
            "j",
            {"ap.nii.gz": "j", "pa.nii.gz": "j-"},
            None,
            [],
            id="missing-readout-time",
        ),
    ],
)
@pytest.mark.parametrize("use_dir_tag", [True, False])
def test_collect_fieldmaps_epi(
    bold_pe_dir: str,
    epi_pe_dirs: dict[str, str],
    total_readout_time: float | None,
    expected: list[str],
    use_dir_tag: bool,
) -> None:
    database = Database(Spec(datetime.now(), list()))

    database.put(mock_bold_file(metadata_phase_encoding_direction=bold_pe_dir, dir="ap" if use_dir_tag else None))
    for path, pe_dir in epi_pe_dirs.items():
        tags = {}
        if use_dir_tag:
            tags["dir"] = path.removesuffix(".nii.gz")

        metadata: dict[str, Any] = dict(phase_encoding_direction=pe_dir)
        if total_readout_time is not None:
            metadata["total_readout_time"] = total_readout_time

        database.put(mock_fmap_file(suffix="epi", metadata=metadata, path=path, tags=tags))

    assert collect_fieldmaps(database, bold_file_path) == sorted(expected)


@pytest.mark.parametrize(
    "field_maps, expected",
    [
        ## phasediff
        pytest.param(
            [
                ("magnitude1", {}),
                ("phasediff", dict(echo_time1=0.00492, echo_time2=0.00738)),
            ],
            ["magnitude1.nii.gz", "phasediff.nii.gz"],
            id="phasediff-with-magnitude1",
        ),
        pytest.param(
            [
                ("magnitude2", {}),
                ("phasediff", dict(echo_time1=0.00492, echo_time2=0.00738)),
            ],
            ["magnitude2.nii.gz", "phasediff.nii.gz"],
            id="phasediff-with-magnitude2",
        ),
        pytest.param(
            [
                ("magnitude1", {}),
                ("magnitude2", {}),
                ("phasediff", dict(echo_time1=0.00492, echo_time2=0.00738)),
            ],
            ["magnitude1.nii.gz", "magnitude2.nii.gz", "phasediff.nii.gz"],
            id="phasediff-with-both-magnitudes",
        ),
        pytest.param(
            [
                ("phasediff", dict(echo_time1=0.00492, echo_time2=0.00738)),
            ],
            [],
            id="phasediff-missing-magnitude",
        ),
        pytest.param(
            [
                ("magnitude1", {}),
                ("magnitude2", {}),
                ("phasediff", {}),
            ],
            ["magnitude1.nii.gz", "magnitude2.nii.gz"],
            id="phasediff-missing-echo-times",
        ),
        ## phase1 phase2
        pytest.param(
            [
                ("magnitude1", {}),
                ("phase1", dict(echo_time=0.00492)),
                ("phase2", dict(echo_time=0.00738)),
            ],
            ["magnitude1.nii.gz", "phase1.nii.gz", "phase2.nii.gz"],
            id="two-phase-with-magnitude1",
        ),
        pytest.param(
            [
                ("magnitude2", {}),
                ("phase1", dict(echo_time=0.00492)),
                ("phase2", dict(echo_time=0.00738)),
            ],
            ["magnitude2.nii.gz", "phase1.nii.gz", "phase2.nii.gz"],
            id="two-phase-with-magnitude2",
        ),
        pytest.param(
            [
                ("magnitude1", {}),
                ("magnitude2", {}),
                ("phase1", dict(echo_time=0.00492)),
                ("phase2", dict(echo_time=0.00738)),
            ],
            ["magnitude1.nii.gz", "magnitude2.nii.gz", "phase1.nii.gz", "phase2.nii.gz"],
            id="two-phase-with-both-magnitudes",
        ),
        pytest.param(
            [("phase1", dict(echo_time=0.00492)), ("phase2", dict(echo_time=0.00738))],
            [],
            id="two-phase-missing-magnitude",
        ),
        pytest.param(
            [("magnitude1", {}), ("phase1", {}), ("phase2", {})],
            ["magnitude1.nii.gz"],
            id="two-phase-missing-echo-times",
        ),
        ## fieldmap
        pytest.param(
            [("fieldmap", dict(units="Hz")), ("magnitude", {})],
            ["fieldmap.nii.gz", "magnitude.nii.gz"],
            id="fieldmap-with-magnitude",
        ),
        pytest.param(
            [("fieldmap", dict(units="Hz"))],
            [],
            id="fieldmap-missing-magnitude",
        ),
        pytest.param(
            [("fieldmap", {}), ("magnitude", {})],
            ["magnitude.nii.gz"],
            id="fieldmap-missing-units",
        ),
    ],
)
@pytest.mark.parametrize("bold_pe_dir", [None, "j"])
def test_collect_fieldmaps_non_epi(bold_pe_dir: str | None, field_maps: list[tuple[str, dict]], expected: list[str]) -> None:
    database = Database(Spec(datetime.now(), list()))

    database.put(mock_bold_file(metadata_phase_encoding_direction=bold_pe_dir))
    for suffix, metadata in field_maps:
        database.put(mock_fmap_file(suffix, metadata))

    assert collect_fieldmaps(database, bold_file_path) == sorted(expected)


bids_cases = [
    # hcp_example_bids
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-01/anat/sub-01_T1w.nii.gz"},
                {"path": "sub-01/fmap/sub-01_acq-forT1w_magnitude1.nii.gz"},
                {"path": "sub-01/fmap/sub-01_acq-forT1w_magnitude2.nii.gz"},
                {
                    "path": "sub-01/fmap/sub-01_acq-forT1w_phasediff.nii.gz",
                    "sidecar": {"EchoTime1": 0.005, "EchoTime2": 0.007, "IntendedFor": ["anat/sub-01_T1w.nii.gz"]},
                },
            ],
            "expected": {"sub-01_task-rest_bold.nii.gz": []},
        },
        id="anat-target-no-leak",
    ),
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/ses-1/func/sub-01_ses-1_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "B0FieldSource": "pepolar_rest",
                    },
                },
                {
                    "path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-rest_dir-AP_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j-", "TotalReadoutTime": 0.05, "B0FieldIdentifier": "pepolar_rest"},
                },
                {
                    "path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-rest_dir-PA_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j", "TotalReadoutTime": 0.05, "B0FieldIdentifier": "pepolar_rest"},
                },
                {
                    "path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-other_dir-AP_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "B0FieldIdentifier": "pepolar_unrequested",
                    },
                },
                {
                    "path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-other_dir-PA_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "B0FieldIdentifier": "pepolar_unrequested",
                    },
                },
            ],
            "expected": {
                "sub-01_ses-1_task-rest_bold.nii.gz": [
                    "sub-01_ses-1_acq-rest_dir-AP_epi.nii.gz",
                    "sub-01_ses-1_acq-rest_dir-PA_epi.nii.gz",
                ]
            },
        },
        id="b0-field-source-excludes-unrequested",
    ),
    # ds006067
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "B0FieldSource": "pepolar_rest",
                    },
                },
                {
                    "path": "sub-01/ses-01/func/sub-01_ses-01_task-faces_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "faces",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "B0FieldSource": "pepolar_faces",
                    },
                },
                {
                    "path": "sub-01/ses-01/fmap/sub-01_ses-01_acq-rest_dir-AP_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "B0FieldIdentifier": "pepolar_rest",
                        "IntendedFor": [],
                    },
                },
                {
                    "path": "sub-01/ses-01/fmap/sub-01_ses-01_acq-rest_dir-PA_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "B0FieldIdentifier": "pepolar_rest",
                        "IntendedFor": [],
                    },
                },
                {
                    "path": "sub-01/ses-01/fmap/sub-01_ses-01_acq-faces_dir-AP_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "B0FieldIdentifier": "pepolar_faces",
                        "IntendedFor": [],
                    },
                },
                {
                    "path": "sub-01/ses-01/fmap/sub-01_ses-01_acq-faces_dir-PA_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "B0FieldIdentifier": "pepolar_faces",
                        "IntendedFor": [],
                    },
                },
            ],
            "expected": {
                "sub-01_ses-01_task-rest_bold.nii.gz": [
                    "sub-01_ses-01_acq-rest_dir-AP_epi.nii.gz",
                    "sub-01_ses-01_acq-rest_dir-PA_epi.nii.gz",
                ],
                "sub-01_ses-01_task-faces_bold.nii.gz": [
                    "sub-01_ses-01_acq-faces_dir-AP_epi.nii.gz",
                    "sub-01_ses-01_acq-faces_dir-PA_epi.nii.gz",
                ],
            },
        },
        id="b0-field-source",
    ),
    # ds000201
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-9050/ses-2/func/sub-9050_ses-2_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-9050/ses-2/func/sub-9050_ses-2_task-hands_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "hands",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-9050/ses-2/fmap/sub-9050_ses-2_magnitude1.nii.gz"},
                {"path": "sub-9050/ses-2/fmap/sub-9050_ses-2_magnitude2.nii.gz"},
                {
                    "path": "sub-9050/ses-2/fmap/sub-9050_ses-2_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.005,
                        "EchoTime2": 0.007,
                        "IntendedFor": ["sub-9050_ses-2_task-rest_bold.nii.gz"],
                    },
                },
            ],
            "expected": {
                "sub-9050_ses-2_task-rest_bold.nii.gz": [
                    "sub-9050_ses-2_magnitude1.nii.gz",
                    "sub-9050_ses-2_magnitude2.nii.gz",
                    "sub-9050_ses-2_phasediff.nii.gz",
                ],
                "sub-9050_ses-2_task-hands_bold.nii.gz": [],
            },
        },
        id="bare-filename-target",
    ),
    # 7t_trt
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-06/ses-1/func/sub-06_ses-1_task-rest_run-1_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-06/ses-1/fmap/sub-06_ses-1_run-1_magnitude1.nii.gz"},
                {"path": "sub-06/ses-1/fmap/sub-06_ses-1_run-1_magnitude2.nii.gz"},
                {
                    "path": "sub-06/ses-1/fmap/sub-06_ses-1_run-1_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.005,
                        "EchoTime2": 0.007,
                        "IntendedFor": "bids::sub-06/ses-1/func/sub-06_ses-1_task-rest_run-1_bold.nii.gz",
                    },
                },
                {
                    "path": "sub-06/ses-1/func/sub-06_ses-1_task-rest_run-2_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-06/ses-1/fmap/sub-06_ses-1_run-2_magnitude1.nii.gz"},
                {"path": "sub-06/ses-1/fmap/sub-06_ses-1_run-2_magnitude2.nii.gz"},
                {
                    "path": "sub-06/ses-1/fmap/sub-06_ses-1_run-2_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.005,
                        "EchoTime2": 0.007,
                        "IntendedFor": "bids::sub-06/ses-1/func/sub-06_ses-1_task-rest_run-2_bold.nii.gz",
                    },
                },
            ],
            "expected": {
                "sub-06_ses-1_task-rest_run-1_bold.nii.gz": [
                    "sub-06_ses-1_run-1_magnitude1.nii.gz",
                    "sub-06_ses-1_run-1_magnitude2.nii.gz",
                    "sub-06_ses-1_run-1_phasediff.nii.gz",
                ],
                "sub-06_ses-1_task-rest_run-2_bold.nii.gz": [
                    "sub-06_ses-1_run-2_magnitude1.nii.gz",
                    "sub-06_ses-1_run-2_magnitude2.nii.gz",
                    "sub-06_ses-1_run-2_phasediff.nii.gz",
                ],
            },
        },
        id="bids-uri",
    ),
    # ds004182
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-AP_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j-", "TotalReadoutTime": 0.05, "IntendedFor": []},
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-PA_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j", "TotalReadoutTime": 0.05, "IntendedFor": []},
                },
            ],
            "expected": {"sub-01_task-rest_bold.nii.gz": ["sub-01_dir-AP_epi.nii.gz", "sub-01_dir-PA_epi.nii.gz"]},
        },
        id="empty-intended-for",
    ),
    # eyetracking_fmri
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-AP_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-01_task-rest_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-PA_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-01_task-rest_bold.nii.gz"],
                    },
                },
                {"path": "sub-01/fmap/sub-01_magnitude.nii.gz"},
                {
                    "path": "sub-01/fmap/sub-01_fieldmap.nii.gz",
                    "sidecar": {"Units": "Hz", "IntendedFor": ["func/sub-01_task-rest_bold.nii.gz"]},
                },
            ],
            "expected": {
                "sub-01_task-rest_bold.nii.gz": [
                    "sub-01_dir-AP_epi.nii.gz",
                    "sub-01_dir-PA_epi.nii.gz",
                    "sub-01_fieldmap.nii.gz",
                    "sub-01_magnitude.nii.gz",
                ]
            },
        },
        id="epi-pair-and-direct-fieldmap",
    ),
    # ds006663
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/func/sub-01_task-faces_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "faces",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-AP_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j-", "TotalReadoutTime": 0.05},
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-PA_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j", "TotalReadoutTime": 0.05},
                },
            ],
            "sidecars": {"epi.json": {"IntendedFor": ["func/sub-01_task-rest_bold.nii.gz"]}},
            "expected": {
                "sub-01_task-rest_bold.nii.gz": ["sub-01_dir-AP_epi.nii.gz", "sub-01_dir-PA_epi.nii.gz"],
                "sub-01_task-faces_bold.nii.gz": [],
            },
        },
        id="inherited-intended-for",
    ),
    # ds006663
    pytest.param(
        {
            "images": [
                {"path": "sub-01/ses-1/func/sub-01_ses-1_task-rest_acq-geEPI_bold.nii.gz"},
                {"path": "sub-01/ses-1/dwi/sub-01_ses-1_acq-b1000_dwi.nii.gz"},
                {"path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-seEPI_dir-IS_epi.nii.gz"},
                {"path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-seEPI_dir-SI_epi.nii.gz"},
                {"path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-DtiEpi_dir-IS_epi.nii.gz"},
                {"path": "sub-01/ses-1/fmap/sub-01_ses-1_acq-DtiEpi_dir-SI_epi.nii.gz"},
            ],
            "sidecars": {
                "task-rest_acq-geEPI_bold.json": {
                    "PulseSequenceType": "Gradient Echo EPI",
                    "PhaseEncodingDirection": "j",
                    "TotalReadoutTime": 0.02016,
                    "EchoTime": 0.015,
                    "FlipAngle": 55,
                    "RepetitionTime": 1.0,
                    "TaskName": "rest",
                },
                "dwi.json": {
                    "PulseSequenceType": "PGSE EPI",
                    "PhaseEncodingDirection": "j",
                    "TotalReadoutTime": 0.0158592,
                    "B0FieldSource": "pepolar_fmap_dwi",
                },
                "acq-seEPI_dir-IS_epi.json": {
                    "PhaseEncodingDirection": "j",
                    "TotalReadoutTime": 0.02016,
                    "B0FieldIdentifier": "pepolar_fmap_bold",
                    "IntendedFor": "bids::sub-SUBJ/ses-SESS/func/sub-SUBJ_ses-SESS_task-rest_acq-geEPI_bold.nii.gz",
                },
                "acq-seEPI_dir-SI_epi.json": {
                    "PhaseEncodingDirection": "j-",
                    "TotalReadoutTime": 0.02016,
                    "B0FieldIdentifier": "pepolar_fmap_bold",
                    "IntendedFor": "bids::sub-SUBJ/ses-SESS/func/sub-SUBJ_ses-SESS_task-rest_acq-geEPI_bold.nii.gz",
                },
                "acq-DtiEpi_dir-IS_epi.json": {
                    "PhaseEncodingDirection": "j",
                    "TotalReadoutTime": 0.0158592,
                    "B0FieldIdentifier": "pepolar_fmap_dwi",
                    "IntendedFor": ["bids::sub-SUBJ/ses-SESS/dwi/sub-SUBJ_ses-SESS_acq-b1000_dwi.nii.gz"],
                },
                "acq-DtiEpi_dir-SI_epi.json": {
                    "PhaseEncodingDirection": "j-",
                    "TotalReadoutTime": 0.0158592,
                    "B0FieldIdentifier": "pepolar_fmap_dwi",
                    "IntendedFor": ["bids::sub-SUBJ/ses-SESS/dwi/sub-SUBJ_ses-SESS_acq-b1000_dwi.nii.gz"],
                },
            },
            "expected": {
                "sub-01_ses-1_task-rest_acq-geEPI_bold.nii.gz": [
                    "sub-01_ses-1_acq-seEPI_dir-IS_epi.nii.gz",
                    "sub-01_ses-1_acq-seEPI_dir-SI_epi.nii.gz",
                ]
            },
        },
        id="inherited-sidecars-only",
    ),
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-01/fmap/sub-01_dir-AP_epi.nii.gz", "sidecar": {"PhaseEncodingDirection": "j-"}},
                {"path": "sub-01/fmap/sub-01_dir-PA_epi.nii.gz", "sidecar": {"PhaseEncodingDirection": "j"}},
            ],
            "sidecars": {"epi.json": {"TotalReadoutTime": 0.05}},
            "expected": {"sub-01_task-rest_bold.nii.gz": ["sub-01_dir-AP_epi.nii.gz", "sub-01_dir-PA_epi.nii.gz"]},
        },
        id="inherited-total-readout-time",
    ),
    # ds000221
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/ses-01/fmap/sub-01_ses-01_dir-AP_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-01/ses-01/fmap/sub-01_ses-01_dir-PA_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz"],
                    },
                },
                {"path": "sub-01/ses-01/fmap/sub-01_ses-01_acq-GEfmap_magnitude1.nii.gz"},
                {"path": "sub-01/ses-01/fmap/sub-01_ses-01_acq-GEfmap_magnitude2.nii.gz"},
                {
                    "path": "sub-01/ses-01/fmap/sub-01_ses-01_acq-GEfmap_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.00519,
                        "EchoTime2": 0.00765,
                        "IntendedFor": ["ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz"],
                    },
                },
            ],
            "expected": {
                "sub-01_ses-01_task-rest_bold.nii.gz": [
                    "sub-01_ses-01_acq-GEfmap_magnitude1.nii.gz",
                    "sub-01_ses-01_acq-GEfmap_magnitude2.nii.gz",
                    "sub-01_ses-01_acq-GEfmap_phasediff.nii.gz",
                    "sub-01_ses-01_dir-AP_epi.nii.gz",
                    "sub-01_ses-01_dir-PA_epi.nii.gz",
                ]
            },
        },
        id="mixed-estimator-families",
    ),
    # ds000117
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/ses-A/func/sub-01_ses-A_task-rest_run-01_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/ses-A/func/sub-01_ses-A_task-rest_run-02_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-01/ses-A/fmap/sub-01_ses-A_magnitude1.nii.gz"},
                {"path": "sub-01/ses-A/fmap/sub-01_ses-A_magnitude2.nii.gz"},
                {
                    "path": "sub-01/ses-A/fmap/sub-01_ses-A_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.005,
                        "EchoTime2": 0.007,
                        "IntendedFor": [
                            "ses-A/func/sub-01_ses-A_task-rest_run-01_bold.nii.gz",
                            "ses-A/func/sub-01_ses-A_task-rest_run-02_bold.nii.gz",
                        ],
                    },
                },
                {
                    "path": "sub-01/ses-B/func/sub-01_ses-B_task-rest_run-01_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/ses-B/func/sub-01_ses-B_task-rest_run-02_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-01/ses-B/fmap/sub-01_ses-B_magnitude1.nii.gz"},
                {"path": "sub-01/ses-B/fmap/sub-01_ses-B_magnitude2.nii.gz"},
                {
                    "path": "sub-01/ses-B/fmap/sub-01_ses-B_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.005,
                        "EchoTime2": 0.007,
                        "IntendedFor": [
                            "ses-B/func/sub-01_ses-B_task-rest_run-01_bold.nii.gz",
                            "ses-B/func/sub-01_ses-B_task-rest_run-02_bold.nii.gz",
                        ],
                    },
                },
            ],
            "expected": {
                "sub-01_ses-A_task-rest_run-01_bold.nii.gz": [
                    "sub-01_ses-A_magnitude1.nii.gz",
                    "sub-01_ses-A_magnitude2.nii.gz",
                    "sub-01_ses-A_phasediff.nii.gz",
                ],
                "sub-01_ses-A_task-rest_run-02_bold.nii.gz": [
                    "sub-01_ses-A_magnitude1.nii.gz",
                    "sub-01_ses-A_magnitude2.nii.gz",
                    "sub-01_ses-A_phasediff.nii.gz",
                ],
                "sub-01_ses-B_task-rest_run-01_bold.nii.gz": [
                    "sub-01_ses-B_magnitude1.nii.gz",
                    "sub-01_ses-B_magnitude2.nii.gz",
                    "sub-01_ses-B_phasediff.nii.gz",
                ],
                "sub-01_ses-B_task-rest_run-02_bold.nii.gz": [
                    "sub-01_ses-B_magnitude1.nii.gz",
                    "sub-01_ses-B_magnitude2.nii.gz",
                    "sub-01_ses-B_phasediff.nii.gz",
                ],
            },
        },
        id="multi-session-phasediff",
    ),
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-AP_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j-", "TotalReadoutTime": 0.05},
                },
                {
                    "path": "sub-01/fmap/sub-01_dir-PA_epi.nii.gz",
                    "sidecar": {"PhaseEncodingDirection": "j", "TotalReadoutTime": 0.05},
                },
            ],
            "expected": {"sub-01_task-rest_bold.nii.gz": ["sub-01_dir-AP_epi.nii.gz", "sub-01_dir-PA_epi.nii.gz"]},
        },
        id="no-intended-for-epi-pair",
    ),
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-01/fmap/sub-01_magnitude1.nii.gz"},
                {"path": "sub-01/fmap/sub-01_magnitude2.nii.gz"},
                {"path": "sub-01/fmap/sub-01_phasediff.nii.gz", "sidecar": {"EchoTime1": 0.005, "EchoTime2": 0.007}},
            ],
            "expected": {
                "sub-01_task-rest_bold.nii.gz": [
                    "sub-01_magnitude1.nii.gz",
                    "sub-01_magnitude2.nii.gz",
                    "sub-01_phasediff.nii.gz",
                ]
            },
        },
        id="no-intended-for-phasediff",
    ),
    # ds000117
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-01/func/sub-01_task-rest_run-01_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/func/sub-01_task-rest_run-02_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-01/func/sub-01_task-rest_run-03_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-01/fmap/sub-01_magnitude1.nii.gz"},
                {"path": "sub-01/fmap/sub-01_magnitude2.nii.gz"},
                {
                    "path": "sub-01/fmap/sub-01_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.005,
                        "EchoTime2": 0.007,
                        "IntendedFor": [
                            "func/sub-01_task-rest_run-01_bold.nii.gz",
                            "func/sub-01_task-rest_run-02_bold.nii.gz",
                            "func/sub-01_task-rest_run-03_bold.nii.gz",
                        ],
                    },
                },
            ],
            "expected": {
                "sub-01_task-rest_run-01_bold.nii.gz": [
                    "sub-01_magnitude1.nii.gz",
                    "sub-01_magnitude2.nii.gz",
                    "sub-01_phasediff.nii.gz",
                ],
                "sub-01_task-rest_run-02_bold.nii.gz": [
                    "sub-01_magnitude1.nii.gz",
                    "sub-01_magnitude2.nii.gz",
                    "sub-01_phasediff.nii.gz",
                ],
                "sub-01_task-rest_run-03_bold.nii.gz": [
                    "sub-01_magnitude1.nii.gz",
                    "sub-01_magnitude2.nii.gz",
                    "sub-01_phasediff.nii.gz",
                ],
            },
        },
        id="one-phasediff-many-runs",
    ),
    # HCP-A
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-HCA01/func/sub-HCA01_task-rest_run-1_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-HCA01/func/sub-HCA01_task-rest_run-2_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-HCA01/func/sub-HCA01_task-rest_run-3_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-HCA01/func/sub-HCA01_task-rest_run-4_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-AP_run-01_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-1_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-AP_run-02_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-2_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-AP_run-03_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-3_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-AP_run-04_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j-",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-4_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-PA_run-01_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-1_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-PA_run-02_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-2_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-PA_run-03_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-3_bold.nii.gz"],
                    },
                },
                {
                    "path": "sub-HCA01/fmap/sub-HCA01_dir-PA_run-04_epi.nii.gz",
                    "sidecar": {
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                        "IntendedFor": ["func/sub-HCA01_task-rest_run-4_bold.nii.gz"],
                    },
                },
            ],
            "expected": {
                "sub-HCA01_task-rest_run-1_bold.nii.gz": [
                    "sub-HCA01_dir-AP_run-01_epi.nii.gz",
                    "sub-HCA01_dir-PA_run-01_epi.nii.gz",
                ],
                "sub-HCA01_task-rest_run-2_bold.nii.gz": [
                    "sub-HCA01_dir-AP_run-02_epi.nii.gz",
                    "sub-HCA01_dir-PA_run-02_epi.nii.gz",
                ],
                "sub-HCA01_task-rest_run-3_bold.nii.gz": [
                    "sub-HCA01_dir-AP_run-03_epi.nii.gz",
                    "sub-HCA01_dir-PA_run-03_epi.nii.gz",
                ],
                "sub-HCA01_task-rest_run-4_bold.nii.gz": [
                    "sub-HCA01_dir-AP_run-04_epi.nii.gz",
                    "sub-HCA01_dir-PA_run-04_epi.nii.gz",
                ],
            },
        },
        id="per-run-pepolar-padding",
    ),
    # ds004341
    pytest.param(
        {
            "images": [
                {
                    "path": "sub-18/func/sub-18_task-rest_bold.nii.gz",
                    "sidecar": {
                        "RepetitionTime": 2.0,
                        "TaskName": "rest",
                        "PhaseEncodingDirection": "j",
                        "TotalReadoutTime": 0.05,
                    },
                },
                {"path": "sub-18/fmap/sub-18_magnitude1.nii.gz"},
                {"path": "sub-18/fmap/sub-18_magnitude2.nii.gz"},
                {
                    "path": "sub-18/fmap/sub-18_phasediff.nii.gz",
                    "sidecar": {
                        "EchoTime1": 0.005,
                        "EchoTime2": 0.007,
                        "IntendedFor": ["bids::sub-18\\sub-18_task-rest_bold.nii.gz"],
                    },
                },
            ],
            "expected": {
                "sub-18_task-rest_bold.nii.gz": [
                    "sub-18_magnitude1.nii.gz",
                    "sub-18_magnitude2.nii.gz",
                    "sub-18_phasediff.nii.gz",
                ]
            },
        },
        id="unresolvable-intended-for",
    ),
]


@pytest.mark.parametrize("case", bids_cases)
def test_collect_fieldmaps_bids(tmp_path: Path, case: dict[str, Any]) -> None:
    for image in case["images"]:
        image_path = tmp_path / image["path"]
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_data = nib.nifti1.Nifti1Image(np.zeros((4, 4, 4, 2), dtype=np.int16), np.eye(4))
        nib.loadsave.save(image_data, image_path)

        sidecar = image.get("sidecar")
        if sidecar is not None:
            sidecar_path = image_path.parent / image_path.name.replace(".nii.gz", ".json")
            with open(sidecar_path, "w") as file_handle:
                json.dump(sidecar, file_handle)

    # Sidecars that are not siblings of an image, so that a case can place metadata higher
    # up the tree and exercise the BIDS inheritance principle
    inherited_sidecars = case.get("sidecars")
    if inherited_sidecars is not None:
        for relative_path, sidecar in inherited_sidecars.items():
            sidecar_path = tmp_path / relative_path
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            with open(sidecar_path, "w") as file_handle:
                json.dump(sidecar, file_handle)

    spec = Spec(datetime.now(), [])
    resolved_spec = ResolvedSpec(spec)
    resolved_spec.resolve(File(str(tmp_path), "bids"))
    database = Database(resolved_spec)

    result: dict[str, list[str]] = dict()
    for fileobj in resolved_spec.resolved_files:
        if fileobj.datatype == "func" and fileobj.suffix == "bold":
            fieldmaps = collect_fieldmaps(database, fileobj.path, silent=True)
            result[Path(fileobj.path).name] = sorted(Path(p).name for p in fieldmaps)

    assert result == case["expected"]


# Reusable metadata fragments for the non-BIDS cases below
phasediff_metadata = dict(echo_time1=0.005, echo_time2=0.007)
epi_ap_metadata = dict(phase_encoding_direction="j-", total_readout_time=0.05)
epi_pa_metadata = dict(phase_encoding_direction="j", total_readout_time=0.05)

# One global pivot shared by every field map, as the UI persists it
acq_to_task = {"acq.se1": ["task.rest"], "acq.se2": ["task.faces"]}

# Non-BIDS inputs carry a UI/TUI-specified ``intended_for`` tag-group mapping on the field
# map ``File`` (the ``{"<fmap_entity>.<value>": ["<bold_entity>.<value>", ...]}`` shape that
# ``AcqToTaskMappingStep`` persists). Each case is (bolds, field_maps, expected): ``bolds``
# is a list of BOLD tag dicts, ``field_maps`` a list of ``_mock_fmap_file`` keyword
# arguments, and ``expected`` maps every BOLD to the sorted field maps it should get.
two_tasks = [dict(task="rest"), dict(task="faces")]


@pytest.mark.parametrize(
    ("bolds", "field_maps", "expected"),
    [
        pytest.param(
            # A field map routed to one task only; the other BOLD gets nothing, and the
            # magnitudes are pruned from it because no field map there uses them.
            two_tasks,
            [
                dict(suffix="magnitude1"),
                dict(suffix="magnitude2"),
                dict(suffix="phasediff", metadata=phasediff_metadata, intended_for={"acq.null": ["task.rest"]}),
            ],
            {
                "rest_bold.nii.gz": ["magnitude1.nii.gz", "magnitude2.nii.gz", "phasediff.nii.gz"],
                "faces_bold.nii.gz": [],
            },
            id="route-to-one-task",
        ),
        pytest.param(
            # A single pivot listing multiple targets serves both BOLDs.
            two_tasks,
            [
                dict(suffix="magnitude1"),
                dict(suffix="magnitude2"),
                dict(
                    suffix="phasediff",
                    metadata=phasediff_metadata,
                    intended_for={"acq.null": ["task.rest", "task.faces"]},
                ),
            ],
            {
                "rest_bold.nii.gz": ["magnitude1.nii.gz", "magnitude2.nii.gz", "phasediff.nii.gz"],
                "faces_bold.nii.gz": ["magnitude1.nii.gz", "magnitude2.nii.gz", "phasediff.nii.gz"],
            },
            id="serve-multiple-tasks",
        ),
        pytest.param(
            # Two opposing epi pairs distinguished by acquisition. Every field map carries the
            # same global pivot (as the UI persists it) and is governed only by its own acq.
            two_tasks,
            [
                dict(
                    path="se1_ap_epi.nii.gz",
                    suffix="epi",
                    tags=dict(acq="se1", dir="ap"),
                    metadata=epi_ap_metadata,
                    intended_for=acq_to_task,
                ),
                dict(
                    path="se1_pa_epi.nii.gz",
                    suffix="epi",
                    tags=dict(acq="se1", dir="pa"),
                    metadata=epi_pa_metadata,
                    intended_for=acq_to_task,
                ),
                dict(
                    path="se2_ap_epi.nii.gz",
                    suffix="epi",
                    tags=dict(acq="se2", dir="ap"),
                    metadata=epi_ap_metadata,
                    intended_for=acq_to_task,
                ),
                dict(
                    path="se2_pa_epi.nii.gz",
                    suffix="epi",
                    tags=dict(acq="se2", dir="pa"),
                    metadata=epi_pa_metadata,
                    intended_for=acq_to_task,
                ),
            ],
            {
                "rest_bold.nii.gz": ["se1_ap_epi.nii.gz", "se1_pa_epi.nii.gz"],
                "faces_bold.nii.gz": ["se2_ap_epi.nii.gz", "se2_pa_epi.nii.gz"],
            },
            id="route-by-acq-to-different-tasks",
        ),
    ],
)
def test_collect_fieldmaps_non_bids_intended_for(
    bolds: list[dict[str, str]],
    field_maps: list[dict],
    expected: dict[str, list[str]],
) -> None:
    database = Database(Spec(datetime.now(), list()))

    bold_file_paths = list()
    for tags in bolds:
        path = f"{tags['task']}_bold.nii.gz"
        bold_file_paths.append(path)
        database.put(mock_bold_file(metadata_phase_encoding_direction="j", path=path, tags=tags))
    for field_map in field_maps:
        database.put(mock_fmap_file(**field_map))

    result = {path: collect_fieldmaps(database, path, silent=True) for path in bold_file_paths}
    assert result == expected


@pytest.mark.slow
@pytest.mark.timeout(120)
def test_collect_fieldmaps_non_bids_intended_for_large() -> None:
    n_subjects = 2_000
    tasks = ["rest", "faces", "sst", "wm"]
    acquisitions = ["mb", "sb"]
    intended_for = {f"acq.{acq}": [f"task.{task}"] for acq, task in zip(acquisitions, tasks, strict=False)}

    database = Database(Spec(datetime.now(), list()))

    bold_file_paths: list[str] = list()
    for subject_index in range(n_subjects):
        sub = f"{subject_index:04d}"
        for task in tasks:
            path = f"sub-{sub}_task-{task}_bold.nii.gz"
            bold_file_paths.append(path)
            database.put(mock_bold_file(metadata_phase_encoding_direction="j", path=path, tags=dict(sub=sub, task=task)))
        for acq in acquisitions:
            for direction, pe_dir in (("ap", "j-"), ("pa", "j")):
                database.put(
                    mock_fmap_file(
                        suffix="epi",
                        path=f"sub-{sub}_acq-{acq}_dir-{direction}_epi.nii.gz",
                        tags=dict(sub=sub, acq=acq, dir=direction),
                        metadata=dict(phase_encoding_direction=pe_dir, total_readout_time=0.05),
                        intended_for=intended_for,
                    )
                )

    for path in bold_file_paths:
        fieldmaps = collect_fieldmaps(database, path, silent=True)
        tags = database.tags(path)
        assert tags is not None
        sub = tags["sub"]
        task = tags["task"]
        if task in tasks[: len(acquisitions)]:
            acq = acquisitions[tasks.index(task)]
            assert fieldmaps == [
                f"sub-{sub}_acq-{acq}_dir-ap_epi.nii.gz",
                f"sub-{sub}_acq-{acq}_dir-pa_epi.nii.gz",
            ]
        else:
            assert fieldmaps == []
