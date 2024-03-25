# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """

import curses


class Color:
    def __init__(self):
        curses.init_pair(1, -1, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_WHITE)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
        curses.init_pair(6, curses.COLOR_RED, curses.COLOR_WHITE)
        curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_WHITE)
        curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        self.default = curses.color_pair(1)
        self.black = curses.color_pair(2)
        self.blue = curses.color_pair(3)
        self.green = curses.color_pair(4)
        self.magenta = curses.color_pair(5)
        self.red = curses.color_pair(6)
        self.cyan = curses.color_pair(7)
        self.yellow = curses.color_pair(8)

        self.white = curses.color_pair(2) | curses.A_REVERSE

        self.idefault = curses.color_pair(1) | curses.A_REVERSE

        self.iblue = curses.color_pair(3) | curses.A_REVERSE
        self.igreen = curses.color_pair(4) | curses.A_REVERSE
        self.imagenta = curses.color_pair(5) | curses.A_REVERSE
        self.ired = curses.color_pair(6) | curses.A_REVERSE
        self.icyan = curses.color_pair(7) | curses.A_REVERSE
        self.iyellow = curses.color_pair(8) | curses.A_REVERSE

        self.palette = [self.ired, self.igreen, self.imagenta, self.icyan]

    def from_string(self, str):
        if hasattr(self, str):
            return getattr(self, str)
        else:
            return self.default
