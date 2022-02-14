# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import numpy as np
import pandas as pd

from ..ops import first_float, first_str


def test_first_float():
    assert first_float([0, 1, 2, 3]) == 0
    assert first_float(list(map(np.uint32, [0, 1, 2, 3]))) == 0
    assert first_float([0., 1., 2., 3.]) == 0.
    assert first_float(np.array([0., 1., 2., 3.])) == 0.
    assert first_float(pd.Series([0., 1., 2., 3.])) == 0.


def test_first_str():
    assert first_str([0, "a"]) == "a"
    assert first_str([None, "a"]) == "a"
    assert first_str([None, Path("a")]) == "a"
