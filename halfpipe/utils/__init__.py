# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .copy import deepcopyfactory, deepcopy
from .format import formatlist, cleaner, formatlikebids
from .hash import hexdigest, b32digest
from .image import niftidim, nvol
from .matrix import loadints, ncol, atleast_4d
from .ops import first, second, firstfloat, firststr, ravel, removenone, lenforeach, ceildiv
from .path import findpaths, splitext, resolve

from inflect import engine
import logging


inflect_engine = engine()
del engine

logger = logging.getLogger("halfpipe")
del logging

__all__ = [
    "inflect_engine",
    "logger",
    "deepcopyfactory",
    "deepcopy",
    "formatlist",
    "cleaner",
    "formatlikebids",
    "hexdigest",
    "b32digest",
    "niftidim",
    "nvol",
    "loadints",
    "ncol",
    "atleast_4d",
    "first",
    "second",
    "firstfloat",
    "firststr",
    "ravel",
    "removenone",
    "lenforeach",
    "ceildiv",
    "findpaths",
    "splitext",
    "resolve",
]
