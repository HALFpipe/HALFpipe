# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def first(obj):
    """
    get first element from iterable or iterator
    """
    from collections.abc import Iterator

    if isinstance(obj, str):  # don't want to get letters from strings
        return obj

    if isinstance(obj, Iterator):
        iterator = obj
    else:
        try:
            iterator = iter(obj)
        except TypeError:
            return obj

    try:
        return next(iterator)
    except StopIteration:
        return  # return None on empty list


def second(obj):
    """
    get second element from iterable
    """
    try:
        it = iter(obj)
        next(it)
        return next(it)
    except TypeError:
        return obj
    except StopIteration:
        return  # return None on empty list


def firstfloat(obj):
    from halfpipe.utils import ravel, first

    obj = ravel(obj)
    return float(first(obj))


def firststr(obj):
    from halfpipe.utils import ravel, first

    obj = ravel(obj)
    return str(first(obj))


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
