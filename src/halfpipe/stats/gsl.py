# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ctypes import CDLL, POINTER, RTLD_GLOBAL, Structure, c_double, c_int

import numpy as np
import scipy

"""
Taken from
https://stats.stackexchange.com/questions/148192/logarithm-of-incomplete-beta-function-for-large-alpha-beta
"""


class gsl_sf_result(Structure):
    _fields_ = [("val", c_double), ("err", c_double)]


gslcblas = CDLL("libgslcblas.so", mode=RTLD_GLOBAL)
gsl = CDLL("libgsl.so")

gsl_sf_hyperg_2F1_e = gsl.gsl_sf_hyperg_2F1_e

gsl_sf_hyperg_2F1_e.restype = c_int
gsl_sf_hyperg_2F1_e.argtypes = [
    c_double,
    c_double,
    c_double,
    c_double,
    POINTER(gsl_sf_result),
]


def gsl_sf_hyperg_2F1(a: float, b: float, c: float, x: float) -> float:
    result = gsl_sf_result()
    code = gsl_sf_hyperg_2F1_e(a, b, c, x, result)
    assert code == 0
    return result.val


def logpbeta(x: float, a: float, b: float) -> float:
    return (
        np.log(gsl_sf_hyperg_2F1(a + b, 1, a + 1, x))
        + a * np.log(x)
        + b * np.log(1 - x)
        - np.log(a)
        - scipy.special.betaln(a, b)
    )


def tdistribution_logcdf(x: float, nu: int):
    if np.isnan(x):
        return np.nan
    elif np.isinf(x):
        return x

    p = scipy.stats.t(nu).cdf(x)
    if np.isfinite(p) and p > 1e-6:
        return np.log(p)

    x_squared = x * x
    z = nu / (nu + x_squared)

    p = logpbeta(
        b=0.5,
        a=nu / 2,
        x=z,
    ) - np.log(2)
    return p


# x, a, b = 0.5555555, 1925.74, 33.7179
# assert np.isclose(gsl_sf_hyperg_2F1(a + b, 1, a + 1, x), 2.298761)
# assert np.isclose(logpbeta(x, a, b), -994.7676)
