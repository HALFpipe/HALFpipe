# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from .config import Config


def get_dir(text):
    if text is None:
        dir = os.curdir
    else:
        dir = op.dirname(text)
    if len(dir) == 0:
        dir = os.curdir
    return dir


def resolve(path) -> str:
    abspath = op.abspath(path)

    fs_root = Config.fs_root

    if not abspath.startswith(fs_root):
        abspath = fs_root + abspath

    return op.normpath(abspath)
