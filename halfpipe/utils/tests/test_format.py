# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pytest

from ..format import formatlikebids


@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "a, b",
    [
        ("seedCorr", "seedCorr"),
        ("faces>shapes", "facesGtShapes"),
        ("faces-vs-shapes", "facesVsShapes"),
        ("fALFF", "fALFF"),
        ("PIAB_1234", "PIAB1234"),
        ("PIAB_1234_MRT1", "PIAB1234MRT1"),
    ]
)
def test_format(a, b):
    assert formatlikebids(a) == b
