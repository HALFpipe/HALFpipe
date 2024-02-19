# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from multiprocessing import active_children

import pytest
from halfpipe.utils.multiprocessing import Pool, make_pool_or_null_context


def fibonacci(i: int) -> int:
    if i < 2:
        return i
    return fibonacci(i - 1) + fibonacci(i - 2)


@pytest.mark.timeout(60)
def test_pool():
    with Pool(processes=2) as pool:
        a = tuple(pool.imap(fibonacci, range(10)))

    assert len(active_children()) == 0

    with Pool(processes=2) as pool:
        b = tuple(pool.imap(fibonacci, range(10)))

    assert len(active_children()) == 0

    assert a == b


def square(x: int) -> int:
    return x**2


@pytest.mark.parametrize("input_data", [[], [1], [1, 2, 3]])
@pytest.mark.parametrize("num_threads", [1, 2])
def test_make_pool_or_null_context(input_data: list[int], num_threads: int):
    cm, iterator = make_pool_or_null_context(
        input_data,
        callable=square,
        num_threads=num_threads,
    )
    with cm:
        assert set(iterator) == {x**2 for x in input_data}
