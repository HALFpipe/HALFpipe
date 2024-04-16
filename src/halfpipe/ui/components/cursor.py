# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """

import curses
import sys

esc = "\u001b["
hide = f"{esc}?25l"
show = f"{esc}?25h"


class Cursor:
    @staticmethod
    def show():
        try:
            curses.curs_set(1)
        except Exception:
            sys.stdout.write(show)
            sys.stdout.flush()

    @staticmethod
    def hide():
        try:
            curses.curs_set(0)
        except Exception:
            sys.stdout.write(hide)
            sys.stdout.flush()
