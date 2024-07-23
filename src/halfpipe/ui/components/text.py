# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """

from abc import ABC, abstractmethod
from typing import List, Optional


class Text(ABC):
    @property
    @abstractmethod
    def value(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def color(self):
        raise NotImplementedError()

    @abstractmethod
    def __len__(self):
        raise NotImplementedError

    def __str__(self) -> str:
        return self.value

    @abstractmethod
    def __iter__(self):
        raise NotImplementedError

    def __lt__(self, other):
        return str(self) < str(other)

    def __eq__(self, other):
        return str(self) == str(other)

    @abstractmethod
    def draw_at(self, y, x, layout, color=None, overridecolor=False, renderfun=None):
        raise NotImplementedError


class TextElement(Text):
    def __init__(self, value, color=None):
        self._color = color
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._color = c

    def __len__(self):
        return len(self._value)

    def __str__(self):
        return self._value

    def __iter__(self):
        for c in self._value:
            yield c, self._color

    def draw_at(self, y, x, layout, color=None, overridecolor=False, renderfun=None):
        if y is None or x is None or layout is None:
            return

        if self.color is not None and not overridecolor:
            color = self.color

        elif color is None:
            color = layout.color.default

        if isinstance(color, str):
            color = layout.color.from_string(color)

        value = self.value
        if renderfun is not None:
            value = renderfun(value)

        layout.window.addstr(y, x, value, color)

        return len(value)


class TextElementCollection(Text):
    def __init__(self, text_elements: Optional[List[Text]] = None):
        if text_elements is None:
            text_elements = list()
        self.text_elements = text_elements

    @property
    def value(self) -> str:
        ret = ""
        for el in self.text_elements:
            ret += str(el)
        return ret

    @property
    def color(self):
        return self.text_elements[0].color

    def append(self, el: Text):
        self.text_elements.append(el)

    def __len__(self):
        return sum(len(el) for el in self.text_elements)

    def __iter__(self):
        for el in self.text_elements:
            yield from el

    def draw_at(self, y, x, layout, color=None, overridecolor=False, renderfun=None):
        size = 0
        for el in self.text_elements:
            el.draw_at(
                y,
                x + size,
                layout,
                color=color,
                overridecolor=overridecolor,
                renderfun=renderfun,
            )
            size += len(el)
        return size
