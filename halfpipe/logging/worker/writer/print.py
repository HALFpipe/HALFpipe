# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys

import stackprinter

from .base import Writer


class PrintWriter(Writer):
    def exception(self):
        sys.stdout.write(stackprinter.format())
        sys.stdout.flush()

    def emit(self, msg: str, levelno: int):
        sys.stdout.write(msg + self.terminator)

    def release(self):
        sys.stdout.flush()
