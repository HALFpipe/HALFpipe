# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def firstfloat(obj):
    import numpy as np
    from typing import Iterable

    if isinstance(obj, float):
        return obj
    elif isinstance(obj, (np.number, int)):
        return float(obj)

    elif isinstance(obj, Iterable):
        for elem in obj:
            elem = firstfloat(elem)

            if isinstance(elem, float):
                return elem


def firststr(obj):
    from pathlib import Path

    if isinstance(obj, str):
        return obj

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, (tuple, list)):
        for elem in obj:
            elem = firststr(elem)

            if isinstance(elem, str):
                return elem


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


def removenone(obj):
    ret = []
    for val in obj:
        if val is None:
            continue
        ret.append(val)
    return ret


def lenforeach(arrarr=None):
    """
    length of each sub-list
    """
    if arrarr is None:
        return []

    return list(map(len, arrarr))


def ceildiv(a, b):
    return -(-a // b)
