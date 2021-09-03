# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from typing import Type, Union
from abc import ABC, abstractclassmethod

import math

from mpmath import mp, mpf, autoprec, mpmathify


def erfinv(a: mpf, tol: float = 1e-16) -> mpf:
    if a == mpf("1") or a == mpf("-1") or abs(a) < 0.9:
        return mp.erfinv(a)

    u = mp.ln(2 / mp.pi / (abs(a) - 1) ** 2)
    x0 = mp.sign(a) * mp.sqrt(u - mp.ln(u)) / mp.sqrt(2)

    def f(t):
        return mp.erf(t) - a

    return mp.findroot(f, x0, tol=tol)


def normppf(p: mpf) -> mpf:
    a = mpf("2") * p - mpf("1")
    return mp.sqrt(mpf("2")) * erfinv(a)  # inverse normal cdf


class Distribution(ABC):
    @abstractclassmethod
    def cdf(cls, *args: mpf) -> mpf:
        raise NotImplementedError

    @classmethod
    def cdfc(cls, *args: mpf) -> mpf:
        return mpf("1") - cls.cdf(*args)


class TDistribution(Distribution):
    @classmethod
    def cdf(cls, x: mpf, nu: mpf) -> mpf:
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

    @classmethod
    def cdfc(cls, x: mpf, nu: mpf) -> mpf:
        return cls.cdf(-x, nu)


class FDistribution(Distribution):
    @staticmethod
    def _integral(x: mpf, d1: mpf, d2: mpf, inv: bool):
        z = d1 * x / (d1 * x + d2)

        if inv is False:
            integral_range = dict(x1=mpf("0"), x2=z)
        else:
            integral_range = dict(x1=z, x2=mpf("1"))

        return mp.betainc(
            d1 / mpf("2"),
            d2 / mpf("2"),
            **integral_range,
            regularized=True,
        )

    @classmethod
    def cdf(cls, x: mpf, d1: mpf, d2: mpf) -> mpf:
        return cls._integral(x, d1, d2, inv=False)

    @classmethod
    def cdfc(cls, x: mpf, d1: mpf, d2: mpf) -> mpf:
        return cls._integral(x, d1, d2, inv=True)


class ChisqDistribution(Distribution):
    @classmethod
    def cdf(cls, x: mpf, k: mpf) -> mpf:
        return mp.gammainc(k / mpf("2"), 0, x / mpf("2"), regularized=True)

    @classmethod
    def cdfc(cls, x: mpf, k: mpf) -> mpf:
        return mp.gammainc(k / mpf("2"), x / mpf("2"), mp.inf, regularized=True)


def auto_convert(
    d: Type[Distribution],
    *args: Union[float, int],
    max_prec: int = 2 ** 13
) -> float:
    if any(math.isnan(a) for a in args):
        return math.nan  # skip computation
    elif math.isinf(args[0]):  # first argument is always the statistic
        return args[0]

    prec = mp.prec

    cdf = d.cdf
    p = cdf(*map(mpmathify, args))

    use_complement = mp.almosteq(p, mpf("1"))
    # it required many more bits to represent a number close to one than a
    # number close to zero
    if use_complement:
        cdf = d.cdfc

    z = math.nan

    try:
        # infer base precision

        while mp.prec < max_prec:
            p = cdf(*map(mpmathify, args))

            if not mp.almosteq(p, mpf("1")) and not mp.almosteq(p, mpf("0")):

                # we have sufficient precision to represent the p-value

                z = float(
                    autoprec(lambda: normppf(cdf(*map(mpf, args))))()
                )

                break

            if mp.prec <= 2 ** 12:
                mp.prec += 2 ** 8
            else:
                mp.prec += 2 ** 12

        # skip calculation

        mp.prec = prec  # reset precision so that almosteq cannot fail

        if not math.isfinite(z):
            if mp.almosteq(p, mpf("1")):
                z = math.inf
            else:
                assert mp.almosteq(p, mpf("0"))
                z = -math.inf

        if use_complement:
            z = -z

        return z
    finally:
        mp.prec = prec


def t2z_convert(x: float, nu: int, **kwargs) -> float:
    return auto_convert(TDistribution, x, nu, **kwargs)


def f2z_convert(x: float, d1: int, d2: int, **kwargs) -> float:

    if x <= 0 or d1 <= 0 or d2 <= 0:
        return -math.inf

    return auto_convert(FDistribution, x, d1, d2, **kwargs)


def chisq2z_convert(x: float, k: int, **kwargs) -> float:

    if x <= mpf("0") or k <= mpf("0"):
        return -math.inf

    return auto_convert(ChisqDistribution, x, k, **kwargs)
