# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from datetime import datetime

import pytest

from ...model.file.base import File
from ...model.spec import Spec
from ..collect import collect_fieldmaps
from ..database import Database


@pytest.mark.parametrize(
    "pe_dirs,expected_count",
    [
        (["j", "j-"], 2),
        (["j", "j"], 0),
    ],
)
def test_collect_fieldmaps_epi(pe_dirs, expected_count):
    database = Database(Spec(datetime.now, list()))

    bold_file_path = "bold.nii.gz"

    files = [
        File(
            path=bold_file_path,
            datatype="func",
            suffix="bold",
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(phase_encoding_direction=pe_dirs[0]),
        ),
        File(
            path="ap.nii.gz",
            datatype="fmap",
            suffix="epi",
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(phase_encoding_direction=pe_dirs[0]),
        ),
        File(
            path="pa.nii.gz",
            datatype="fmap",
            suffix="epi",
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(phase_encoding_direction=pe_dirs[1]),
        ),
    ]

    for file in files:
        database.put(file)

    fieldmaps = collect_fieldmaps(database, bold_file_path)
    assert len(fieldmaps) == expected_count


@pytest.mark.parametrize(
    "case1_suffix, case1_count",
    [
        (["", "", "phasediff"], 0),
        (["magnitude1", "", "phasediff"], 3),
        (["magnitude1", "magnitude2", "phasediff"], 3),
    ],
)
def test_collect_fieldmaps_phasediff(case1_suffix, case1_count):
    database = Database(Spec(datetime.now, list()))

    bold_file_path = "bold.nii.gz"

    files = [
        # Phase Difference Maps and atleast one magnitude image
        File(
            path="magnitude1.nii.gz",
            datatype="fmap",
            suffix=case1_suffix[0],
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(echo_time_1=4.63),
        ),
        File(
            path="magnitude2.nii.gz",
            datatype="fmap",
            suffix=case1_suffix[1],
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(echo_time_2=7.09),
        ),
        File(
            path="phasediff.nii.gz",
            datatype="fmap",
            suffix=case1_suffix[2],
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
        File(
            path=bold_file_path,
            datatype="func",
            suffix="bold",
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
    ]

    for file in files:
        database.put(file)

    fieldmaps = collect_fieldmaps(database, bold_file_path)
    assert len(fieldmaps) == case1_count


@pytest.mark.parametrize(
    "case2_suffix, case2_count",
    [
        (["", "", "", ""], 0),
        (["", "", "phase1", ""], 0),
        (["", "", "phase1", "phase2"], 2),
        (["magnitude1", "", "phase1", "phase2"], 4),
        (["", "magnitude2", "phase1", "phase2"], 4),
        (["magnitude1", "magnitude2", "phase1", "phase2"], 4),
    ],
)
def test_collect_fieldmaps_twophase(case2_suffix, case2_count):
    database = Database(Spec(datetime.now, list()))

    bold_file_path = "bold.nii.gz"

    files = [
        File(
            path="magnitude1.nii.gz",
            datatype="fmap",
            suffix=case2_suffix[0],
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(echo_time_1=None),
        ),
        File(
            path="magnitude2.nii.gz",
            datatype="fmap",
            suffix=case2_suffix[1],
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(echo_time_2=None),
        ),
        File(
            path="phase1.nii.gz",
            datatype="fmap",
            suffix=case2_suffix[2],
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
        File(
            path="phase2.nii.gz",
            datatype="fmap",
            suffix=case2_suffix[3],
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
        File(
            path=bold_file_path,
            datatype="func",
            suffix="bold",
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
    ]

    for file in files:
        database.put(file)

    fieldmaps = collect_fieldmaps(database, bold_file_path)
    assert len(fieldmaps) == case2_count


@pytest.mark.parametrize(
    "case3_suffix, case3_count",
    [
        (["fieldmap", "magnitude"], 2),
        (["fieldmap", ""], 0),
        (["", "magnitude"], 0),
    ],
)
def test_collect_fieldmaps_direct(case3_suffix, case3_count):
    database = Database(Spec(datetime.now, list()))

    bold_file_path = "bold.nii.gz"

    files = [
        File(
            path="fieldmap.nii.gz",
            datatype="fmap",
            suffix=case3_suffix[0],
            extension=".nii.gz",
            tags=dict(sub="01"),
            metadata=dict(units=("Hz", "rad/s", "T")),
        ),
        File(
            path="magnitude.nii.gz",
            datatype="fmap",
            suffix=case3_suffix[1],
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
        File(
            path=bold_file_path,
            datatype="func",
            suffix="bold",
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
    ]

    for file in files:
        database.put(file)

    fieldmaps = collect_fieldmaps(database, bold_file_path)
    assert len(fieldmaps) == case3_count
