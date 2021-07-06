# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import numpy as np
import pandas as pd

from ..ops import firstfloat, firststr


def test_firstfloat():
    assert firstfloat([0, 1, 2, 3]) == 0
    assert firstfloat(list(map(np.uint32, [0, 1, 2, 3]))) == 0
    assert firstfloat([0., 1., 2., 3.]) == 0.
    assert firstfloat(np.array([0., 1., 2., 3.])) == 0.
    assert firstfloat(pd.Series([0., 1., 2., 3.])) == 0.


def test_firststr():
    assert firststr([0, "a"]) == "a"
    assert firststr([None, "a"]) == "a"
    assert firststr([None, Path("a")]) == "a"
