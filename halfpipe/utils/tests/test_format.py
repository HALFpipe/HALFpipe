# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pytest

from ..format import formatlikebids


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "a, b",
    [
        ("seedCorr", "seedCorr"),
        ("faces>shapes", "facesGtShapes"),
        ("faces-vs-shapes", "facesVsShapes"),
    ]
)
def test_format(a, b):
    assert formatlikebids(a) == b
