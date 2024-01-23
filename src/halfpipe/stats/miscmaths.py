# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys

import numpy as np
from llvmlite import binding
from numba import njit, vectorize
from numba.core import types, typing

if sys.platform == "darwin":
    binding.load_library_permanently("libRmath.dylib")  # pragma: no cover
else:
    binding.load_library_permanently("libRmath.so")  # pragma: no cover
c_pt = types.ExternalFunction(
    "pt",
    typing.Signature(
        return_type=types.double,
        args=[types.double, types.double, types.intc, types.intc],
        recvr=None,
    ),
)
c_pf = types.ExternalFunction(
    "pf",
    typing.Signature(
        return_type=types.double,
        args=[types.double, types.double, types.double, types.intc, types.intc],
        recvr=None,
    ),
)
c_pchisq = types.ExternalFunction(
    "pchisq",
    typing.Signature(
        return_type=types.double,
        args=[types.double, types.double, types.intc, types.intc],
        recvr=None,
    ),
)
c_qnorm = types.ExternalFunction(
    "qnorm5",
    typing.Signature(
        return_type=types.double,
        args=[types.double, types.double, types.double, types.intc, types.intc],
        recvr=None,
    ),
)
c_fetestexcept = types.ExternalFunction(
    "fetestexcept",
    typing.Signature(
        return_type=types.intc,
        args=[types.intc],
        recvr=None,
    ),
)
c_feclearexcept = types.ExternalFunction(
    "feclearexcept",
    typing.Signature(
        return_type=types.intc,
        args=[types.intc],
        recvr=None,
    ),
)


@njit
def clear_floatstatus() -> None:
    if c_fetestexcept(31) != 0:
        c_feclearexcept(31)


@njit
def pt(
    x: float,
    degrees_of_freedom: float,
    lower_tail: bool = True,
    log_p: bool = False,
) -> float:
    return c_pt(x, degrees_of_freedom, np.int32(lower_tail), np.int32(log_p))


@njit
def pf(
    x: float,
    numerator_degrees_of_freedom: float,
    denominator_degrees_of_freedom: float,
    lower_tail: bool = True,
    log_p: bool = False,
) -> float:
    return c_pf(
        x,
        numerator_degrees_of_freedom,
        denominator_degrees_of_freedom,
        np.int32(lower_tail),
        np.int32(log_p),
    )


@njit
def pchisq(
    x: float,
    degrees_of_freedom: float,
    lower_tail: bool = True,
    log_p: bool = False,
) -> float:
    return c_pchisq(x, degrees_of_freedom, np.int32(lower_tail), np.int32(log_p))


@njit
def qnorm(
    p: float,
    mu: float = 0.0,
    sigma: float = 1.0,
    lower_tail: bool = True,
    log_p: bool = False,
) -> float:
    return c_qnorm(p, mu, sigma, np.int32(lower_tail), np.int32(log_p))


@vectorize([types.double(types.double, types.double)])
def t2z_convert(
    x: float,
    degrees_of_freedom: float,
) -> float:
    lower_tail: bool = x < 0
    log_p = pt(x, degrees_of_freedom, lower_tail=lower_tail, log_p=True)
    z: float = qnorm(p=log_p, lower_tail=lower_tail, log_p=True)
    clear_floatstatus()
    return z


@vectorize([types.double(types.double, types.double, types.double)])
def f2z_convert(
    x: float,
    numerator_degrees_of_freedom: float,
    denominator_degrees_of_freedom: float,
) -> float:
    lower_tail: bool = x < 1
    log_p = pf(
        x,
        numerator_degrees_of_freedom,
        denominator_degrees_of_freedom,
        lower_tail=lower_tail,
        log_p=True,
    )
    z: float = qnorm(p=log_p, lower_tail=lower_tail, log_p=True)
    clear_floatstatus()
    return z


@vectorize([types.double(types.double, types.double)])
def chisq2z_convert(
    x: float,
    degrees_of_freedom: float,
) -> float:
    lower_tail: bool = x < 0
    log_p = pchisq(x, degrees_of_freedom, lower_tail=lower_tail, log_p=True)
    z: float = qnorm(p=log_p, lower_tail=lower_tail, log_p=True)
    clear_floatstatus()
    return z
