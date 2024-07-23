# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import curses
import functools
import itertools
from typing import Self

import numpy as np

from .cursor import Cursor
from .font import font
from .layout import Layout
from .text import Text, TextElement

longest_readable_line_width = 100


class View:
    counter = itertools.count()

    def __init__(self, color=None, emphasis_color=None, highlight_color=None):
        self.id = next(View.counter)

        self.color = color
        self.emphasis_color = emphasis_color
        self.highlight_color = highlight_color

        self._layout: Layout | None = None

        self._view_width: int = 100

    def __repr__(self):
        return f"View[id={self.id}]"

    @property
    def layout(self) -> Layout:
        if self._layout is None:
            raise ValueError("View is not part of a layout")
        return self._layout

    def setup(self):
        # cannot do this in constructor, as curses may not be initialized yet
        if self.color is None:
            self.color = self.layout.color.black
        if self.highlight_color is None:
            self.highlight_color = self.layout.color.white
        if self.emphasis_color is None:
            self.emphasis_color = self.layout.color.iblue
        self.emphasis_color |= curses.A_BOLD

    def draw_at(self, y):
        raise NotImplementedError

    def draw(self):
        try:
            y = self.layout.offset(self)
            if y is None:
                return
            size = self.draw_at(y)
            self._set_view_size(size)
        except ValueError:
            pass  # view was removed

    def update(self) -> Self:
        self.layout.app.dispatch(self.draw)
        return self

    def appendto(self, layout):
        layout.append(self)
        self.setup()
        return self.update()

    def focus(self):
        self.layout.focus(self)
        return self

    def erase_at(self, y, n: int | None = None):
        if n is None:
            n = self._get_view_size()
        if n is not None:
            for i in range(n):
                self.layout.window.move(y + i, 0)
                self.layout.window.clrtoeol()
        return 0

    def erase(self):
        y = self.layout.offset(self)
        if y is not None:
            size = self.erase_at(y)
            self._set_view_size(size)

    def _show_cursor(self):
        self.layout.app.dispatch(Cursor.show)

    def _hide_cursor(self):
        self.layout.app.dispatch(Cursor.hide)

    def _clear_status_bar(self):
        self.layout.app.dispatch(self.layout.clear_status_bar)

    def _set_status_bar(self, text):
        self.layout.app.dispatch(functools.partial(self.layout.set_status_bar, text))

    def _get_view_width(self):
        return self._view_width

    def _get_view_size(self) -> int | None:
        return self.layout.get_view_size(self)

    def _set_view_size(self, new_size):
        self.layout.set_view_size(self, new_size=new_size)


class SpacerView(View):
    def __init__(self, n, **kwargs):
        super(SpacerView, self).__init__(**kwargs)
        self.n = n

    def draw_at(self, y):
        self.erase_at(y, n=self.n)
        return self.n


class TextView(View):
    def __init__(self, text, **kwargs):
        super(TextView, self).__init__(**kwargs)
        if not isinstance(text, Text):
            text = TextElement(text)
        self.text = text

    def draw_at(self, y):
        self.text.draw_at(y, 0, self.layout, self.color)
        if len(self.text) > self._view_width:
            self._view_width = len(self.text)
        return 1


class GiantTextView(View):
    def __init__(self, text, **kwargs):
        super(GiantTextView, self).__init__(**kwargs)
        self.text = text

    def draw_at(self, y):
        binarray = np.hstack([font[c] for c in self.text])
        for i in range(binarray.shape[0]):
            for j in range(binarray.shape[1]):
                attr = self.color
                if not isinstance(attr, int):
                    raise ValueError("Color must be an int")
                if binarray[i, j]:
                    attr |= curses.A_REVERSE
                self.layout.window.addch(y + i, j * 2 + 0, " ", attr)
                self.layout.window.addch(y + i, j * 2 + 1, " ", attr)
        if binarray.shape[1] > self._view_width:
            self._view_width = binarray.shape[1]
        return binarray.shape[0]


class CallableView(View):
    def __init__(self, **kwargs):
        super(CallableView, self).__init__(**kwargs)
        self.is_active = False

    def __call__(self):
        self._before_call()
        self.focus()

        self.is_active = True
        self.update()

        while self.is_active:
            c = self.layout.keyboard.queue.get()
            self._handle_key(c)

        self.is_active = False
        self._after_call()
        self.update()

        return self._get_output()

    def _before_call(self):
        raise NotImplementedError

    def _after_call(self):
        self._clear_status_bar()

    def _handle_key(self, c):
        raise NotImplementedError

    def _get_output(self):
        raise NotImplementedError
