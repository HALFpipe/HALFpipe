# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from contextlib import AbstractContextManager


class chdir(AbstractContextManager):
    """
    Non thread-safe context manager to change the current working directory.

    Taken from https://github.com/python/cpython/commit/3592980f9122ab0d9ed93711347742d110b749c2
    """

    def __init__(self, path):
        self.path = path
        self._old_cwd = []

    def __enter__(self):
        self._old_cwd.append(os.getcwd())
        os.chdir(self.path)

    def __exit__(self, *excinfo):
        os.chdir(self._old_cwd.pop())
