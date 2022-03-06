# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import Type

import numpy as np

from ..keyboard import Key
from ..text import Text, TextElement
from ..view import CallableView
from .choice import MultiSingleChoiceInputView, SingleChoiceInputView


def common_chars(inlist):
    inlist = [str(s) for s in inlist]
    k = min(len(s) for s in inlist)
    ret = ""
    for i in range(k):
        ls = set(s[i] for s in inlist)
        if len(ls) == 1:
            ret += ls.pop()
        else:
            break
    return ret


def _tokenize(text):
    return TextElement(f"[{text}]")


class TextInputView(CallableView):
    def __init__(
        self,
        text=None,
        isokfun=None,
        messagefun=None,
        tokenizefun=None,
        nchr_prepend=0,
        forbidden_chars="",
        maxlen=-1,
        **kwargs,
    ):
        super(TextInputView, self).__init__(**kwargs)
        self.text = text
        self.previousLength = None
        self.cur_index = 0

        self.isokfun = isokfun
        if self.isokfun is None:
            self.isokfun = self._is_ok

        self.messagefun = messagefun

        self.nchr_prepend = nchr_prepend

        self.tokenizefun = tokenizefun
        if self.tokenizefun is None:
            self.tokenizefun = _tokenize
            self.nchr_prepend = 1

        self.forbidden_chars = forbidden_chars
        self.maxlen = maxlen

    def _before_call(self):
        if self.text is None:
            self.text = ""
        self._setStatusBar(
            "  ".join(["[↵] Ok", "[← →] Move cursor", "[ctrl-c] Cancel"])
        )

    def _is_ok(self):
        return True

    def _handleKey(self, c):
        if c == Key.Break:
            self.text = None
            self.isActive = False
        elif c == Key.Return:
            if self._is_ok():
                self.isActive = False
        elif c == Key.Left:
            self.cur_index = max(0, self.cur_index - 1)
            self.update()
        elif c == Key.Right:
            self.cur_index = min(len(self.text), self.cur_index + 1)
            self.update()
        elif c == Key.Backspace:
            if self.cur_index > 0:
                self.text = (
                    self.text[: self.cur_index - 1] + self.text[self.cur_index :]
                )
                self.cur_index -= 1
                self.update()
        elif c == Key.Delete:
            if self.cur_index < len(self.text):
                self.text = (
                    self.text[: self.cur_index] + self.text[self.cur_index + 1 :]
                )
                self.update()
        elif isinstance(c, Key):
            pass
        elif self.forbidden_chars.find(chr(c)) != -1:
            pass
        elif self.maxlen > 0 and len(self.text) >= self.maxlen:
            pass
        else:
            self.text = (
                self.text[: self.cur_index] + chr(c) + self.text[self.cur_index :]
            )
            self.cur_index += 1
            self.update()

    def _getOutput(self):
        return self.text

    def drawAt(self, y, x=0):
        if y is None:
            return
        curLength = None
        if self.text is not None:
            text: Text = self.tokenizefun(self.text)
            curLength = len(text)
            for c, color in text:
                if color is None:
                    color = self.color
                if (
                    self.isActive
                    and self.cur_index is not None
                    and x == self.cur_index + self.nchr_prepend
                ):
                    color = self.emphasisColor
                self.layout.window.addstr(y, x, c, color)
                x += 1

        if self.previousLength is not None:
            for i in range(x, self.previousLength + 1):
                self.layout.window.addch(y, i, " ", self.layout.color.default)

        if self.messagefun is not None:
            message = self.messagefun()
            if message is not None:
                x += 1
                x += message.drawAt(y, x, self.layout)

        if curLength is not None:
            self.previousLength = x

        if x > self._viewWidth:
            self._viewWidth = x

        return 1


class NumberInputView(TextInputView):
    def __init__(
        self,
        number=0,
        min=-np.inf,
        max=np.inf,
        **kwargs,
    ):
        super(NumberInputView, self).__init__(text=str(number), **kwargs)
        self.min = min
        self.max = max

    def _is_ok(self):
        try:
            number = float(self.text)
            return self.min <= number <= self.max
        except ValueError:
            return False

    def _handleKey(self, c):
        if isinstance(c, Key) or chr(c) in "0123456789.e-":
            super(NumberInputView, self)._handleKey(c)

    def _getOutput(self):
        if self.text is not None:
            return float(self.text)


class MultiTextInputView(SingleChoiceInputView):
    text_input_type: Type[TextInputView] = TextInputView

    def __init__(self, options, initial_values=None, **kwargs):
        super_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k in {"color", "emphasisColor", "highlightColor"}
        }
        super(MultiTextInputView, self).__init__(
            options,
            isVertical=True,
            addBrackets=False,
            showSelectionAfterExit=False,
            **super_kwargs,
        )
        self.selectedIndices = None
        self.optionWidth = max(len(option) for option in options)

        if initial_values is None:
            initial_values = [None] * len(options)
        kwargs.update(
            dict(nchr_prepend=self.optionWidth + 1 + 1, tokenizefun=_tokenize)
        )
        self.children = [
            self.text_input_type(**kwargs)
            if val is None
            else self.text_input_type(val, **kwargs)
            for val in initial_values
        ]
        for child in self.children:
            child.update = self.update

    def setup(self):
        super(MultiTextInputView, self).setup()
        for child in self.children:
            child.layout = self.layout
            child.setup()

    def _before_call(self):
        super(MultiTextInputView, self)._before_call()
        actions = [
            "[↵] Ok",
            "[← →] Move cursor",
            "[↑ ↓] Change selection",
            "[ctrl-c] Cancel",
        ]
        self._setStatusBar("  ".join(actions))
        for child in self.children:
            child._before_call()
        self.children[self.cur_index].isActive = True

    def _handleKey(self, c):
        if (
            c == Key.Left
            or c == Key.Right
            or c == Key.Backspace
            or c == Key.Delete
            or not isinstance(c, Key)
        ):
            if self.cur_index is not None:
                self.children[self.cur_index]._handleKey(c)
            self.update()
        else:
            prev_index = self.cur_index
            super(MultiTextInputView, self)._handleKey(c)
            if self.cur_index is not None and prev_index != self.cur_index:
                self.children[prev_index].isActive = False
                self.children[self.cur_index].isActive = True
            elif self.cur_index is None or not self.isActive:
                self.children[prev_index].isActive = False

    def _is_ok(self):
        return all(child._is_ok() for child in self.children)

    def _getOutput(self):
        if self.cur_index is not None:  # was not cancelled
            return {
                str(option): child._getOutput()
                for option, child in zip(self.options, self.children)
            }

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        if self.cur_index is not None and i == self.cur_index and self.isActive:
            color = self.emphasisColor
        option.drawAt(y, x, self.layout, color)
        x += self.optionWidth
        x += 1

        self.children[i].drawAt(y, x)
        x += self.children[i]._viewWidth

        return x


class MultiNumberInputView(MultiTextInputView):
    text_input_type = NumberInputView


class MultiCombinedTextAndSingleChoiceInputView(MultiSingleChoiceInputView):
    text_input_type: Type[TextInputView] = TextInputView

    def __init__(self, options, values, initial_values=None, **kwargs):
        super_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k in {"color", "emphasisColor", "highlightColor"}
        }

        if not isinstance(values[0], list):
            values = [[*values] for _ in options]

        for i in range(len(values)):
            values[i].insert(0, "")

        super().__init__(
            options,
            values,
            addBrackets=True,
            **super_kwargs,
        )

        self.optionWidth = max(len(option) for option in options)
        self.option_spacing = 0
        if self.optionWidth > 0:
            self.option_spacing = 1

        if initial_values is None:
            initial_values = [None] * len(options)

        kwargs.update(
            dict(
                nchr_prepend=self.optionWidth + self.option_spacing + 1,
                tokenizefun=_tokenize,
            )
        )

        self.initialSelectedIndices = [0] * len(self.options)

        self.children = []
        for i, val in enumerate(initial_values):
            for j, choiceval in enumerate(values[i]):
                if str(val) == str(choiceval):
                    self.initialSelectedIndices[i] = j
                    val = None
                    break
            if val is None:
                self.children.append(self.text_input_type(**kwargs))
            else:
                self.children.append(self.text_input_type(val, **kwargs))

        for child in self.children:
            child.update = self.update

    def setup(self):
        super(MultiCombinedTextAndSingleChoiceInputView, self).setup()
        for child in self.children:
            child.layout = self.layout
            child.setup()

    def _before_call(self):
        if self.selectedIndices is None:
            self.selectedIndices = [*self.initialSelectedIndices]
        super(MultiCombinedTextAndSingleChoiceInputView, self)._before_call()
        actions = [
            "[↵] Ok",
            "[← →] Move cursor",
            "[↑ ↓] Change selection",
            "[ctrl-c] Cancel",
        ]
        self._setStatusBar("  ".join(actions))
        for child in self.children:
            child._before_call()
        if self.selectedIndices[self.cur_index] == 0:
            self.children[self.cur_index].isActive = True

    def _handleKey(self, c):
        # left right navigation
        if self.cur_index is not None and self.selectedIndices is not None:
            if self.selectedIndices[self.cur_index] == 0:
                child = self.children[self.cur_index]
                child_len = len(child.text)
                child_index = child.cur_index
                if child_index == child_len and c == Key.Right:
                    child.isActive = False
                    super(MultiCombinedTextAndSingleChoiceInputView, self)._handleKey(c)
                    return
                elif (
                    c == Key.Left
                    or c == Key.Right
                    or c == Key.Backspace
                    or c == Key.Delete
                    or not isinstance(c, Key)
                ):
                    child._handleKey(c)
                    return
        prev_index = self.cur_index
        super(MultiCombinedTextAndSingleChoiceInputView, self)._handleKey(c)
        # up down navigation
        if self.cur_index is not None and self.selectedIndices is not None:
            if self.selectedIndices[self.cur_index] == 0:
                self.children[self.cur_index].isActive = True

        if (
            prev_index is not None
            and prev_index != self.cur_index
            and prev_index is not None
        ):
            self.children[prev_index].isActive = False

        if not self.isActive:
            for child in self.children:
                child.isActive = False

        self.update()

    def _is_ok(self):
        return all(child._is_ok() for child in self.children)

    def _getOutput(self):
        if self.selectedIndices is not None:
            return {
                str(k): str(self.values[i][v])
                if v > 0
                else self.children[i]._getOutput()
                for i, (k, v) in enumerate(zip(self.options, self.selectedIndices))
            }

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        option.drawAt(y, 0, self.layout, color)
        x += self.optionWidth + self.option_spacing

        for j, value in enumerate(self.values[i]):
            color = self.color
            if self.selectedIndices is not None:
                if j == self.selectedIndices[i]:
                    color = self.highlightColor

            if j == 0:
                self.children[i].color = color
                self.children[i].drawAt(y, x=x)
                x = self.children[i].previousLength
            else:
                if color == self.highlightColor:
                    if (
                        self.cur_index is not None
                        and i == self.cur_index
                        and self.isActive
                    ):
                        color = self.emphasisColor

                if self._add_brackets:
                    self.layout.window.addstr(y, x, "[", color)
                    x += 1
                nchr = value.drawAt(y, x, self.layout, color)
                x += nchr
                if self._add_brackets:
                    self.layout.window.addstr(y, x, "]", color)
                    x += 1
            self.layout.window.addstr(y, x, " ", self.layout.color.default)
            x += 1

        return x


class MultiCombinedNumberAndSingleChoiceInputView(
    MultiCombinedTextAndSingleChoiceInputView
):
    text_input_type = NumberInputView
