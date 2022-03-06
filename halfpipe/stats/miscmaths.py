# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import math
from abc import ABC, abstractmethod

from mpmath import autoprec, mp, mpf, mpmathify


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
    @abstractmethod
    def cdf(self, x: mpf) -> mpf:
        raise NotImplementedError

    def cdfc(self, x: mpf) -> mpf:
        return mpf("1") - self.cdf(x)

    def auto_convert(self, x: float, max_prec: int = 2**13) -> float:
        if math.isnan(x):
            return math.nan  # skip computation

        elif math.isinf(x):
            return x

        prec = mp.prec

        cdf = self.cdf
        p = cdf(mpmathify(x))

        use_complement = mp.almosteq(p, mpf("1"))
        # it required many more bits to represent a number close to one than a
        # number close to zero
        if use_complement:
            cdf = self.cdfc

        z = math.nan

        try:
            # infer base precision

            while mp.prec < max_prec:
                p = cdf(mpmathify(x))

                if not mp.almosteq(p, mpf("1")) and not mp.almosteq(p, mpf("0")):

                    # we have sufficient precision to represent the p-value

                    calc_z = autoprec(lambda: normppf(cdf(mpmathify(x))))
                    z = float(calc_z())

                    break

                if mp.prec <= 2**12:
                    mp.prec += 2**8
                else:
                    mp.prec += 2**12

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


class TDistribution(Distribution):
    def __init__(self, nu: int) -> None:
        super().__init__()

        self.nu: int = nu

    def cdf(self, x: mpf) -> mpf:
        nu = mpmathify(self.nu)

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

    def cdfc(self, x: mpf) -> mpf:
        return self.cdf(-x)


class FDistribution(Distribution):
    def __init__(self, d1: int, d2: int) -> None:
        super().__init__()

        self.d1: int = d1
        self.d2: int = d2

    def _integral(self, x: mpf, inv: bool):
        d1 = mpmathify(self.d1)
        d2 = mpmathify(self.d2)

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

    def cdf(self, x: mpf) -> mpf:
        return self._integral(x, inv=False)

    def cdfc(self, x: mpf) -> mpf:
        return self._integral(x, inv=True)


class ChisqDistribution(Distribution):
    def __init__(self, k: int) -> None:
        super().__init__()

        self.k: int = k

    def cdf(self, x: mpf) -> mpf:
        k = mpmathify(self.k)
        return mp.gammainc(k / mpf("2"), 0, x / mpf("2"), regularized=True)

    def cdfc(self, x: mpf) -> mpf:
        k = mpmathify(self.k)
        return mp.gammainc(k / mpf("2"), x / mpf("2"), mp.inf, regularized=True)


def t2z_convert(x: float, nu: int, **kwargs) -> float:
    return TDistribution(nu).auto_convert(x, **kwargs)


def f2z_convert(x: float, d1: int, d2: int, **kwargs) -> float:

    if x <= 0 or d1 <= 0 or d2 <= 0:
        return -math.inf

    return FDistribution(d1, d2).auto_convert(x, **kwargs)


def chisq2z_convert(x: float, k: int, **kwargs) -> float:

    if x <= mpf("0") or k <= mpf("0"):
        return -math.inf

    return ChisqDistribution(k).auto_convert(x, **kwargs)
