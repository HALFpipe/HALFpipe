# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from datetime import datetime
from typing import Any

import pytest

from halfpipe.collect.fmap import PhaseEncodingDirection, check_opposing_pe, collect_fieldmaps
from halfpipe.ingest.database import Database
from halfpipe.model.file.base import File
from halfpipe.model.spec import Spec

bold_file_path = "bold.nii.gz"


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


def _mock_bold_file(metadata_phase_encoding_direction: str | None = None, dir: str | None = None) -> File:
    tags = dict(sub="01")
    if dir is not None:
        tags["dir"] = dir
    metadata = dict()
    if metadata_phase_encoding_direction is not None:
        metadata["phase_encoding_direction"] = metadata_phase_encoding_direction
    return File(
        path=bold_file_path,
        datatype="func",
        suffix="bold",
        extension=".nii.gz",
        tags=tags,
        metadata=metadata,
    )


def _mock_epi_file(
    path: str,
    dir: str | None = None,
    phase_encoding_direction: str | None = None,
    total_readout_time: float | None = 0.05,
) -> File:
    tags = dict(sub="01")
    if dir is not None:
        tags["dir"] = dir
    metadata: dict[str, Any] = dict()
    if phase_encoding_direction is not None:
        metadata["phase_encoding_direction"] = phase_encoding_direction
    if total_readout_time is not None:
        metadata["total_readout_time"] = total_readout_time
    return File(
        path=path,
        datatype="fmap",
        suffix="epi",
        extension=".nii.gz",
        tags=tags,
        metadata=metadata,
    )


def _mock_fmap_file(suffix: str, metadata: dict) -> File:
    return File(
        path=suffix + ".nii.gz",
        datatype="fmap",
        suffix=suffix,
        extension=".nii.gz",
        tags=dict(sub="01"),
        metadata=dict(metadata),  # copy so shared parametrization dicts are never mutated
    )


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

    database.put(_mock_bold_file(metadata_phase_encoding_direction=bold_pe_dir, dir="ap" if use_dir_tag else None))
    for path, pe_dir in epi_pe_dirs.items():
        database.put(
            _mock_epi_file(
                path,
                dir=path.removesuffix(".nii.gz") if use_dir_tag else None,
                phase_encoding_direction=pe_dir,
                total_readout_time=total_readout_time,
            )
        )

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

    database.put(_mock_bold_file(metadata_phase_encoding_direction=bold_pe_dir))
    for suffix, metadata in field_maps:
        database.put(_mock_fmap_file(suffix, metadata))

    assert collect_fieldmaps(database, bold_file_path) == sorted(expected)
