# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path

import pytest
from nipype.interfaces.base.support import Bunch

from ..path import find_paths, split_ext, validate_workdir

A = "a.txt"
B = "b.txt"


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "obj",
    [
        [A, B],
        (A, B),
        {A, B},
        {"a": A, "b": B},
        {"x": {"y": [A, B]}},
        Bunch(a=A, b=B),
        Bunch(x=[A, B]),
    ],
)
def test_find_paths(tmp_path, obj):
    os.chdir(str(tmp_path))

    for fname in [A, B]:
        Path(fname).touch()

    assert set(find_paths(obj)) == set([A, B])

    for fname in [A, B]:
        Path(fname).unlink()


def test_split_ext():
    assert split_ext("a/a.nii.gz") == ("a", ".nii.gz")
    assert split_ext("a/a.pickle.xz") == ("a", ".pickle.xz")

@pytest.mark.parametrize(
    "workdir, is_valid",
    [
        (None, False),
        (int(), False),
        (float(), False),
        ([], False),
        ({}, False),
        ("NOTDIR", False),
    ],
)
def test_invalid_workdir(workdir, is_valid):
    assert validate_workdir(workdir) == is_valid


def test_valid_workdir(tmp_path):
    assert validate_workdir(tmp_path) == True
