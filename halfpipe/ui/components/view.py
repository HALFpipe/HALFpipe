# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
import curses
import functools
import itertools
from typing import Optional

import numpy as np

from .cursor import Cursor
from .font import font
from .layout import Layout
from .text import Text, TextElement

longestReadableLineWidth = 100


class View:
    counter = itertools.count()

    def __init__(self, color=None, emphasisColor=None, highlightColor=None):
        self.id = next(View.counter)

        self.color = color
        self.emphasisColor = emphasisColor
        self.highlightColor = highlightColor

        self.layout: Optional[Layout] = None

        self._viewWidth: int = 100

    def __repr__(self):
        return f"View[id={self.id}]"

    def setup(self):
        # cannot do this in constructor, as curses may not be initialized yet
        if self.color is None:
            self.color = self.layout.color.black
        if self.highlightColor is None:
            self.highlightColor = self.layout.color.white
        if self.emphasisColor is None:
            self.emphasisColor = self.layout.color.iblue
        self.emphasisColor |= curses.A_BOLD

    def drawAt(self, y):
        raise NotImplementedError

    def draw(self):
        try:
            y = self.layout.offset(self)
            if y is None:
                return
            size = self.drawAt(y)
            self._setViewSize(size)
        except ValueError:
            pass  # view was removed

    def update(self):
        self.layout.app.dispatch(self.draw)
        return self

    def appendto(self, layout):
        layout.append(self)
        self.setup()
        return self.update()

    def focus(self):
        self.layout.focus(self)
        return self

    def eraseAt(self, y, n=None):
        if n is None:
            n = self._getViewSize()
        for i in range(n):
            self.layout.window.move(y + i, 0)
            self.layout.window.clrtoeol()
        return 0

    def erase(self):
        y = self.layout.offset(self)
        if y is not None:
            size = self.eraseAt(y)
            self._setViewSize(size)

    def _showCursor(self):
        self.layout.app.dispatch(Cursor.show)

    def _hideCursor(self):
        self.layout.app.dispatch(Cursor.hide)

    def _clearStatusBar(self):
        self.layout.app.dispatch(self.layout.clearStatusBar)

    def _setStatusBar(self, text):
        self.layout.app.dispatch(functools.partial(self.layout.setStatusBar, text))

    def _getViewWidth(self):
        return self._viewWidth

    def _getViewSize(self):
        return self.layout.getViewSize(self)

    def _setViewSize(self, newsize):
        self.layout.setViewSize(self, newSize=newsize)


class SpacerView(View):
    def __init__(self, n, **kwargs):
        super(SpacerView, self).__init__(**kwargs)
        self.n = n

    def drawAt(self, y):
        self.eraseAt(y, n=self.n)
        return self.n


class TextView(View):
    def __init__(self, text, **kwargs):
        super(TextView, self).__init__(**kwargs)
        if not isinstance(text, Text):
            text = TextElement(text)
        self.text = text

    def drawAt(self, y):
        self.text.drawAt(y, 0, self.layout, self.color)
        if len(self.text) > self._viewWidth:
            self._viewWidth = len(self.text)
        return 1


class GiantTextView(View):
    def __init__(self, text, **kwargs):
        super(GiantTextView, self).__init__(**kwargs)
        self.text = text

    def drawAt(self, y):
        binarray = np.hstack([font[c] for c in self.text])
        for i in range(binarray.shape[0]):
            for j in range(binarray.shape[1]):
                attr = self.color
                if binarray[i, j]:
                    attr |= curses.A_REVERSE
                self.layout.window.addch(y + i, j * 2 + 0, " ", attr)
                self.layout.window.addch(y + i, j * 2 + 1, " ", attr)
        if binarray.shape[1] > self._viewWidth:
            self._viewWidth = binarray.shape[1]
        return binarray.shape[0]


class CallableView(View):
    def __init__(self, **kwargs):
        super(CallableView, self).__init__(**kwargs)
        self.isActive = False

    def __call__(self):
        self._before_call()
        self.focus()

        self.isActive = True
        self.update()

        while self.isActive:
            c = self.layout.keyboard.queue.get()
            self._handleKey(c)

        self.isActive = False
        self._after_call()
        self.update()

        return self._getOutput()

    def _before_call(self):
        raise NotImplementedError

    def _after_call(self):
        self._clearStatusBar()

    def _handleKey(self, c):
        raise NotImplementedError

    def _getOutput(self):
        raise NotImplementedError
