# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import pytest

import sys
import math

import numpy as np
from scipy import stats

from ..miscmaths import t2z_convert, f2z_convert, chisq2z_convert


def t2z_convert_numpy(t, dof):
    p = stats.t.cdf(t, dof)
    z = stats.norm.ppf(p)

    return z


def f2z_convert_numpy(f, dof1, dof2):
    p = stats.f.cdf(f, dof1, dof2)
    z = stats.norm.ppf(p)

    return z


def chisq2z_convert_numpy(x, k):
    p = stats.chi2.cdf(x, k)
    z = stats.norm.ppf(p)

    return z


# numpy comparisons

@pytest.mark.parametrize("t", np.linspace(-7, 7, num=5))
@pytest.mark.parametrize("dof", [2, 10, 30])
def test_t2z_convert_numpy(t, dof):
    assert math.isclose(t2z_convert(t, dof), t2z_convert_numpy(t, dof))


@pytest.mark.parametrize("f", np.linspace(1e-3, 7, num=10))
@pytest.mark.parametrize("d1,d2", [
    (1, 1), (2, 1), (5, 2), (10, 1), (10, 100)
])
def test_f2z_convert_numpy(f, d1, d2):
    assert math.isclose(f2z_convert(f, d1, d2), f2z_convert_numpy(f, d1, d2))


@pytest.mark.parametrize("x", np.linspace(1e-3, 7, num=10))
@pytest.mark.parametrize("k", [2, 10, 30])
def test_chisq2z_convert_numpy(x, k):
    assert math.isclose(chisq2z_convert(x, k), chisq2z_convert_numpy(x, k))


# large number tests

@pytest.mark.parametrize("t", np.logspace(1, 4, num=5))
@pytest.mark.parametrize("dof", [2, 10, 30])
def test_t2z_convert_large(t, dof):
    z = t2z_convert(t, dof)
    assert math.isfinite(z)
    assert math.isclose(z, -t2z_convert(-t, dof))  # symmetric


@pytest.mark.parametrize("x", np.logspace(1, 3, num=5))
@pytest.mark.parametrize("k", [2, 10, 30])
def test_chisq2z_convert_large(x, k):
    assert math.isfinite(chisq2z_convert(x, k))


@pytest.mark.parametrize("f", np.logspace(2, 4, num=5))
@pytest.mark.parametrize("d1,d2", [
    (10, 20), (10, 100)
])
def test_f2z_convert_large(f, d1, d2):
    assert math.isfinite(f2z_convert(f, d1, d2))


# huge number tests

@pytest.mark.parametrize("t", [
    *np.logspace(5, 100, num=10),
    sys.float_info.max,
])
@pytest.mark.parametrize("dof", [30])
@pytest.mark.slow
@pytest.mark.timeout(120)
def test_t2z_convert_huge(t, dof):
    z = t2z_convert(t, dof)
    assert math.isclose(z, -t2z_convert(-t, dof))  # symmetric


@pytest.mark.parametrize("x", [
    sys.float_info.min,
    *np.logspace(-100, -4, num=10),
    *np.logspace(4, 100, num=10),
    sys.float_info.max,
])
@pytest.mark.parametrize("k", [30])
@pytest.mark.slow
@pytest.mark.timeout(120)
def test_chisq2z_convert_huge(x, k):
    assert isinstance(chisq2z_convert(x, k), float)


@pytest.mark.parametrize("f", [
    sys.float_info.min,
    *np.logspace(-100, -4, num=10),
    *np.logspace(5, 100, num=10),
    sys.float_info.max,
])
@pytest.mark.parametrize("d1,d2", [
    (10, 100),
])
@pytest.mark.slow
@pytest.mark.timeout(120)
def test_f2z_convert_huge(f, d1, d2):
    assert isinstance(f2z_convert(f, d1, d2), float)


@pytest.mark.slow
@pytest.mark.timeout(1)
def test_nonfinite():
    assert t2z_convert(np.inf, 1) == np.inf
    assert t2z_convert(-np.inf, 1) == -np.inf
    assert math.isnan(t2z_convert(np.nan, 1))

    assert f2z_convert(np.inf, 1, 1) == np.inf
    assert f2z_convert(-np.inf, 1, 1) == -np.inf
    assert math.isnan(f2z_convert(np.nan, 1, 1))

    assert chisq2z_convert(np.inf, 1) == np.inf
    assert chisq2z_convert(-np.inf, 1) == -np.inf
    assert math.isnan(chisq2z_convert(np.nan, 1))


def test_gmpy():
    from mpmath.libmp import BACKEND
    assert BACKEND == "gmpy"
