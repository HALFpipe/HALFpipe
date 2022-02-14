# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pytest

import os
from pathlib import Path

from nipype.interfaces.base.support import Bunch

from ..path import find_paths


A = "/tmp/a.txt"  # TODO make this more elegant with a tmp_dir
B = "/tmp/b.txt"


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
        Bunch(x=[A, B])
    ]
)
def test_findpaths(tmp_path, obj):
    os.chdir(str(tmp_path))

    for fname in [A, B]:
        Path(fname).touch()

    assert set(find_paths(obj)) == set([A, B])

    for fname in [A, B]:
        Path(fname).unlink()
