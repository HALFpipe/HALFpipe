# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from datetime import datetime

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


def _mock_epi_file(path: str, metadata_phase_encoding_direction: str, dir: str | None = None) -> File:
    tags = dict(sub="01")
    if dir is not None:
        tags["dir"] = dir
    return File(
        path=path,
        datatype="fmap",
        suffix="epi",
        extension=".nii.gz",
        tags=tags,
        metadata=dict(phase_encoding_direction=metadata_phase_encoding_direction),
    )


def _mock_fmap_file(suffix: str) -> File:
    return File(
        path=suffix + ".nii.gz",
        datatype="fmap",
        suffix=suffix,
        extension=".nii.gz",
        tags=dict(sub="01"),
    )


def _collect(database: Database, *files: File) -> list[str]:
    for file in files:
        database.put(file)
    return collect_fieldmaps(database, bold_file_path)


@pytest.mark.parametrize(
    "bold_pe_dir, epi_pe_dirs, expected",
    [
        # Opposing pair
        ("j", {"ap.nii.gz": "j", "pa.nii.gz": "j-"}, ["ap.nii.gz", "pa.nii.gz"]),
        # All same direction
        ("j", {"ap.nii.gz": "j", "pa.nii.gz": "j"}, []),
        # Different axis
        ("j", {"i.nii.gz": "i", "i-.nii.gz": "i-"}, []),
        # Opposing pair and different axis
        ("j", {"ap.nii.gz": "j", "pa.nii.gz": "j-", "lr.nii.gz": "i"}, ["ap.nii.gz", "pa.nii.gz"]),
    ],
)
@pytest.mark.parametrize("use_dir_tag", [True, False])
def test_collect_fieldmaps_epi(bold_pe_dir: str, epi_pe_dirs: dict[str, str], expected: list[str], use_dir_tag: bool) -> None:
    database = Database(Spec(datetime.now(), list()))

    files = [_mock_bold_file(metadata_phase_encoding_direction=bold_pe_dir, dir="ap" if use_dir_tag else None)]
    files += [
        _mock_epi_file(path, pe_dir, dir=path.removesuffix(".nii.gz") if use_dir_tag else None)
        for path, pe_dir in epi_pe_dirs.items()
    ]

    assert sorted(_collect(database, *files)) == sorted(expected)


@pytest.mark.parametrize(
    "case1_suffix, case1_count",
    [
        (["", "", ""], 0),
        (["", "", "phasediff"], 0),
        (["magnitude1", "", "phasediff"], 2),
        (["", "magnitude2", "phasediff"], 2),
        (["magnitude1", "magnitude2", "phasediff"], 3),
    ],
)
@pytest.mark.parametrize("bold_pe_dir", [None, "j"])
def test_collect_fieldmaps_phasediff(bold_pe_dir, case1_suffix, case1_count):
    database = Database(Spec(datetime.now(), list()))

    suffixes = ["magnitude1", "magnitude2", "phasediff"]
    files = [_mock_fmap_file(suffix) for suffix in case1_suffix if suffix in suffixes]
    files.append(_mock_bold_file(metadata_phase_encoding_direction=bold_pe_dir))
    if len(files) < 3:
        files.clear()

    assert len(_collect(database, *files)) == case1_count


@pytest.mark.parametrize(
    "case2_suffix, case2_count",
    [
        (["", "", "", ""], 0),
        (["", "", "phase1", ""], 0),
        (["", "", "phase1", "phase2"], 0),
        (["magnitude1", "", "phase1", "phase2"], 3),
        (["", "magnitude2", "phase1", "phase2"], 3),
        (["magnitude1", "magnitude2", "phase1", "phase2"], 4),
    ],
)
def test_collect_fieldmaps_twophase(case2_suffix, case2_count):
    database = Database(Spec(datetime.now(), list()))

    suffixes = ["magnitude1", "magnitude2", "phase1", "phase2"]
    files = [_mock_fmap_file(suffix) for suffix in case2_suffix if suffix in suffixes]
    files.append(_mock_bold_file())
    if len(files) < 4:
        files.clear()

    assert len(_collect(database, *files)) == case2_count


@pytest.mark.parametrize(
    "case3_suffix, case3_count",
    [
        (["fieldmap", "magnitude"], 2),
        (["fieldmap", ""], 0),
        (["", "magnitude"], 0),
        (["", ""], 0),
    ],
)
def test_collect_fieldmaps_direct(case3_suffix, case3_count):
    database = Database(Spec(datetime.now(), list()))

    suffixes = ["fieldmap", "magnitude"]
    files = [_mock_fmap_file(suffix) for suffix in case3_suffix if suffix in suffixes]
    files.append(_mock_bold_file())
    if len(files) < 3:  # clear files if expected count will be 0 (counting bold file as well here)
        files.clear()

    assert len(_collect(database, *files)) == case3_count
