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
        (["", "", ""], 0),
        (["", "", "phasediff"], 0),
        (["magnitude1", "", "phasediff"], 2),
        (["", "magnitude2", "phasediff"], 2),
        (["magnitude1", "magnitude2", "phasediff"], 3),
    ],
)
def test_collect_fieldmaps_phasediff(case1_suffix, case1_count):
    database = Database(Spec(datetime.now, list()))

    bold_file_path = "bold.nii.gz"
    vars = ["magnitude1", "magnitude2", "phasediff"]
    files = []
    for i in case1_suffix:
        if i in vars:
            files.append(
                File(
                    path=i + ".nii.gz",
                    datatype="fmap",
                    suffix=i,
                    extension=".nii.gz",
                    tags=dict(sub="01"),
                    # metadata=dict(echo_time_1=4.63),
                )
            )
    files.append(
        File(
            path=bold_file_path,
            datatype="func",
            suffix="bold",
            extension=".nii.gz",
            tags=dict(sub="01"),
        )
    )
    if len(files) < 3:
        files.clear()

    for file in files:
        database.put(file)

    fieldmaps = collect_fieldmaps(database, bold_file_path)
    assert len(fieldmaps) == case1_count


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
    database = Database(Spec(datetime.now, list()))

    bold_file_path = "bold.nii.gz"
    vars = ["magnitude1", "magnitude2", "phase1", "phase2"]
    files = []
    for i in case2_suffix:
        if i in vars:
            files.append(
                File(
                    path=i + ".nii.gz",
                    datatype="fmap",
                    suffix=i,
                    extension=".nii.gz",
                    tags=dict(sub="01"),
                )
            )
    files.append(
        File(
            path=bold_file_path,
            datatype="func",
            suffix="bold",
            extension=".nii.gz",
            tags=dict(sub="01"),
        ),
    )

    if len(files) < 4:
        files.clear()

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
        (["", ""], 0),
    ],
)
def test_collect_fieldmaps_direct(case3_suffix, case3_count):
    database = Database(Spec(datetime.now, list()))

    bold_file_path = "bold.nii.gz"
    vars = ["fieldmap", "magnitude"]
    files = []
    for i in case3_suffix:
        if i in vars:
            files.append(
                File(
                    path=i + ".nii.gz",
                    datatype="fmap",
                    suffix=i,
                    extension=".nii.gz",
                    tags=dict(sub="01"),
                    # metadata=dict(units=("Hz", "rad/s", "T")),
                )
            )
    files.append(
        File(
            path=bold_file_path,
            datatype="func",
            suffix="bold",
            extension=".nii.gz",
            tags=dict(sub="01"),
        )
    )
    if (
        len(files) < 3
    ):  # clear files if expected count will be 0 (counting bold file as well here)
        files.clear()

    for file in files:
        database.put(file)

    fieldmaps = collect_fieldmaps(database, bold_file_path)
    assert len(fieldmaps) == case3_count
