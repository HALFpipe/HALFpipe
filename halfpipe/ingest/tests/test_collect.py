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
