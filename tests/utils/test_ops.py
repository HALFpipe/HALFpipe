# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from halfpipe.utils.ops import check_almost_equal, first_float, first_str


def test_first_float():
    assert first_float([0, 1, 2, 3]) == 0
    assert first_float(list(map(np.uint32, [0, 1, 2, 3]))) == 0
    assert first_float([0.0, 1.0, 2.0, 3.0]) == 0.0
    assert first_float(np.array([0.0, 1.0, 2.0, 3.0])) == 0.0
    assert first_float(pd.Series([0.0, 1.0, 2.0, 3.0])) == 0.0


def test_first_str():
    assert first_str([0, "a"]) == "a"
    assert first_str([None, "a"]) == "a"
    assert first_str([None, Path("a")]) == "a"


def test_check_almost_equal() -> None:
    a: Any = 100000000001 / 100000000000
    b: Any = 1

    assert check_almost_equal(a, b) is True
    assert check_almost_equal(a, 2) is False

    a = [a] * 100
    b = [b] * 100
    assert check_almost_equal(a, b) is True

    b.pop()
    assert check_almost_equal(a, b) is False

    a = dict(a=a[0], b=b[0])
    b = dict(a=b[0], b=b[0])
    assert check_almost_equal(a, b) is True
