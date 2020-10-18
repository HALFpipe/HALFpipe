# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .copy import deepcopyfactory, deepcopy
from .format import formatlist, cleaner, formatlikebids
from .hash import hexdigest, b32digest
from .image import niftidim, nvol
from .matrix import loadints, ncol
from .ops import first, second, firstfloat, firststr, ravel, removenone, lenforeach
from .path import findpaths, splitext

from inflect import engine


inflect_engine = engine()
del engine

__all__ = [
    inflect_engine,
    deepcopyfactory, deepcopy,
    formatlist, cleaner, formatlikebids,
    hexdigest, b32digest,
    niftidim, nvol,
    loadints, ncol,
    first, second, firstfloat, firststr, ravel, removenone, lenforeach,
    findpaths, splitext
]
