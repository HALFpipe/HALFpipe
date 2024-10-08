# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pytest

from halfpipe.utils.format import format_like_bids, format_workflow


@pytest.mark.parametrize(
    "a, b",
    [
        ("seedCorr", "seedCorr"),
        ("faces>shapes", "facesGtShapes"),
        ("faces-vs-shapes", "facesVsShapes"),
        ("fALFF", "fALFF"),
        ("PIAB_1234", "PIAB1234"),
        ("PIAB_1234_MRT1", "PIAB1234MRT1"),
        ("", ""),
    ],
)
def test_format(a, b):
    assert format_like_bids(a) == b


@pytest.mark.parametrize(
    "a, b",
    [
        ("seedCorr", "seed_corr"),
        ("faces>shapes", "faces_gt_shapes"),
        ("faces-vs-shapes", "faces_vs_shapes"),
        ("fALFF", "f_alff"),
        ("PIAB_1234", "piab_1234"),
        ("PIAB_1234_MRT1", "piab_1234_mrt1"),
        ("", ""),
    ],
)
def test_workflow(a, b):
    assert format_workflow(a) == b
