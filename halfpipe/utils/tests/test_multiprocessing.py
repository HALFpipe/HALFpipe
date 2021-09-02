# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from multiprocessing import active_children

from ..multiprocessing import Pool


def fibonacci(i: int):
    if i < 2:
        return i
    return fibonacci(i - 1) + fibonacci(i - 2)


def test_pool():
    with Pool() as pool:
        a = tuple(pool.map(fibonacci, range(10)))

    assert len(active_children()) == 0

    with Pool() as pool:
        b = tuple(pool.map(fibonacci, range(10)))

    assert len(active_children()) == 0

    assert a == b
