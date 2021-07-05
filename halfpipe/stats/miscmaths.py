# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from typing import Callable, Union

import math

from mpmath import mp, mpf, autoprec, mpmathify


def erfinv(a: mpf, tol: float = 1e-16) -> mpf:
    if a == mpf("1") or a == mpf("-1") or abs(a) < 0.9:
        return mp.erfinv(a)

    u = mp.ln(2 / mp.pi / (abs(a) - 1)**2)
    x0 = mp.sign(a) * mp.sqrt(u - mp.ln(u)) / mp.sqrt(2)

    def f(t):
        return mp.erf(t) - a

    return mp.findroot(f, x0, tol=tol)


def normppf(p: mpf) -> mpf:
    a = mpf("2") * p - mpf("1")
    return mp.sqrt(mpf("2")) * erfinv(a)  # inverse normal cdf


def tcdf(x: mpf, nu: mpf) -> mpf:
    x2 = x * x
    z = nu / (nu + x2)
    p = mp.betainc(
        nu / mpf("2"),
        mpf("1") / mpf("2"),
        x1=mpf("0"),
        x2=z,
        regularized=True,
    ) / mpf("2")

    if x > mpf("0"):
        return mpf("1") - p
    else:
        return p


def fcdf(x: mpf, d1: mpf, d2: mpf) -> mpf:
    return mp.betainc(
        d1 / mpf("2"),
        d2 / mpf("2"),
        x1=mpf("0"),
        x2=d1 * x / (d1 * x + d2),
        regularized=True,
    )


def chisqcdf(x: mpf, k: mpf) -> mpf:
    a = k / mpf("2")

    return mp.gammainc(a, 0, x / mpf("2")) / mp.gamma(a)


def auto_convert(cdf: Callable, *args: Union[float, int]) -> float:
    if any(math.isnan(a) for a in args):
        return math.nan  # skip computation

    if math.isinf(args[0]):  # first argument is always the statistic
        return args[0]

    prec = mp.prec

    try:
        # infer base precision

        p = cdf(*map(mpmathify, args))

        while mp.prec < 2 ** 14:
            p = cdf(*map(mpmathify, args))

            if not mp.almosteq(p, mpf("1")) and not mp.almosteq(p, mpf("0")):

                # we have sufficient precision to represent the p-value

                return float(
                    autoprec(lambda: normppf(cdf(*map(mpf, args))))()
                )

            if mp.prec <= 2 ** 12:
                mp.prec += 2 ** 8
            else:
                mp.prec += 2 ** 12

        # skip calculation

        mp.prec = prec  # reset precision so that almosteq cannot fail

        if mp.almosteq(p, mpf("1")):
            return math.inf
        elif mp.almosteq(p, mpf("0")):
            return -math.inf

        raise RuntimeError()  # should never be reached

    finally:
        mp.prec = prec


def t2z_convert(x: float, nu: int) -> float:
    return auto_convert(tcdf, x, nu)


def f2z_convert(x: float, d1: int, d2: int) -> float:

    if x <= 0 or d1 <= 0 or d2 <= 0:
        return -math.inf

    return auto_convert(fcdf, x, d1, d2)


def chisq2z_convert(x: float, k: int) -> float:

    if x <= mpf("0") or k <= mpf("0"):
        return -math.inf

    return auto_convert(chisqcdf, x, k)
