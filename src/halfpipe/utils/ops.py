# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from itertools import zip_longest
from math import isclose
from typing import Any, Collection, Mapping, Sequence

import numpy as np


def first_float(obj) -> float | None:
    from typing import Iterable

    import numpy as np

    if isinstance(obj, float):
        return obj
    elif isinstance(obj, (np.number, int)):
        return float(obj)
    elif isinstance(obj, Iterable):
        for elem in obj:
            elem = first_float(elem)

            if isinstance(elem, float):
                return elem

    return None


def first_str(obj) -> str | None:
    from pathlib import Path

    if isinstance(obj, str):
        return obj

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, (tuple, list)):
        for x in obj:
            x = first_str(x)

            if isinstance(x, str):
                return x

    return None


def ravel(obj):
    if isinstance(obj, (str, dict)):
        return obj

    try:
        ret = []
        for val in obj:
            raveled_val = ravel(val)
            if not isinstance(raveled_val, (str, dict)):
                try:
                    ret.extend(raveled_val)
                    continue
                except TypeError:
                    pass
            ret.append(raveled_val)
        return ret

    except TypeError:
        return obj
    except StopIteration:
        return []  # empty input
    except Exception:
        return []


def len_for_each(arrarr=None):
    """
    length of each sub-list
    """
    if arrarr is None:
        return []

    return list(map(len, arrarr))


def check_almost_equal(a: Any, b: Any) -> bool:
    """
    Recursively compare data structures for equality while using `math.isclose` for floats.

    Args:
        a (Any): The first value to compare.
        b (Any): The second value to compare.

    Returns:
        bool: True if the values are almost equal, False otherwise.
    """
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        return check_almost_equal(sorted(a.items()), sorted(b.items()))

    elif isinstance(a, str) and isinstance(b, str):
        pass

    elif isinstance(a, Sequence) and isinstance(b, Sequence):
        return all(check_almost_equal(x, y) for x, y in zip_longest(a, b))

    elif isinstance(a, Collection) and isinstance(b, Collection):
        return check_almost_equal(sorted(a), sorted(b))

    elif isinstance(a, (float, int, np.number)) and isinstance(b, (float, int, np.number)):
        return isclose(a, b)

    return a == b
