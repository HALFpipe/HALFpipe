# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys
import logging

from .base import Writer


class PrintWriter(Writer):
    def emit(self, msg: str, levelno: int):
        if levelno >= logging.WARNING:
            sys.stderr.write(msg + self.terminator)
        else:
            sys.stdout.write(msg + self.terminator)

    def release(self):
        sys.stdout.flush()
        sys.stderr.flush()
