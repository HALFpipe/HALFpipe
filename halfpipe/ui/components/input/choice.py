# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
from typing import Dict, List, Optional

from ..keyboard import Key
from ..text import Text, TextElement
from ..view import CallableView


class SingleChoiceInputView(CallableView):
    def __init__(
        self,
        options,
        label=None,
        cur_index=None,
        isVertical=False,
        addBrackets=True,
        showSelectionAfterExit=True,
        renderfun=None,
        colorfun=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.isVertical = isVertical
        self.addBrackets = addBrackets
        self.showSelectionAfterExit = showSelectionAfterExit

        self.cur_index: Optional[int] = cur_index

        self.clearBeforeDrawSize = 0
        self.offset = 0
        self.renderfun = renderfun
        self.colorfun = colorfun

        self.label = label
        self.options: List = list()
        self.set_options(options)

    def set_options(self, newoptions):
        self.offset = 0
        for i in range(len(newoptions)):
            if not isinstance(newoptions[i], Text):
                newoptions[i] = TextElement(newoptions[i])
        if self.options is not None:
            self.clearBeforeDrawSize = max(self.clearBeforeDrawSize, len(self.options))
        self.options = newoptions
        if self.cur_index is not None and self.cur_index > len(newoptions):
            self.cur_index = 0

    def _is_ok(self):
        return True

    def _before_call(self):
        if self.cur_index is None:
            self.cur_index = 0
        arrows = "← →"
        if self.isVertical:
            arrows = "↑ ↓"
        self._setStatusBar(
            "  ".join(["[↵] Ok", f"[{arrows}] Change selection", "[ctrl-c] Cancel"])
        )

    def _handleKey(self, c):
        if c == Key.Break:
            self.cur_index = None
            self.update()
            self.isActive = False
        elif c == Key.Return:
            if self._is_ok():
                self.isActive = False
        elif (self.isVertical and c == Key.Up) or (
            not self.isVertical and c == Key.Left
        ):
            self.cur_index = max(0, self.cur_index - 1)
            self.update()
        elif (
            (self.isVertical and c == Key.Down)
            or (not self.isVertical and c == Key.Right)
            or c == Key.Tab
        ):
            self.cur_index = min(len(self.options) - 1, self.cur_index + 1)
            self.update()
        elif isinstance(c, Key):
            pass
        else:
            pass

    def _getOutput(self):
        if self.cur_index is not None:
            return str(self.options[self.cur_index])

    def _drawAt_horizontal(self, y):
        if y is None:
            return
        x = 0
        if self.label is not None:
            self.layout.window.addstr(y, x, self.label, self.color)
            x += self.columnWidth
            x += 1
        for i, option in enumerate(self.options):
            color = self.color
            if i == self.cur_index:
                if self.isActive:
                    color = self.emphasisColor
                elif self.showSelectionAfterExit:
                    color = self.highlightColor
            if self.addBrackets:
                self.layout.window.addstr(y, x, "[", color)
                x += 1
            nchr = option.drawAt(y, x, self.layout, color, renderfun=self.renderfun)
            x += nchr
            if self.addBrackets:
                self.layout.window.addstr(y, x, "]", color)
                x += 1
            x += 1

        if x > self._viewWidth:
            self._viewWidth = x

        return 1

    def _draw_text(self, y, text, color):
        nchr = text.drawAt(y, 0, self.layout, color)
        nothing = " " * (self._viewWidth - nchr)
        self.layout.window.addstr(y, nchr, nothing, self.layout.color.default)
        return nchr

    def _draw_option(self, i, y):
        if y is None:
            return
        if i >= len(self.options):
            nothing = " " * self._viewWidth
            self.layout.window.addstr(y, 0, nothing, self.layout.color.default)
            return
        option = self.options[i]
        color = self.color
        overridecolor = False
        if self.cur_index is not None:
            if i == self.cur_index and self.isActive:
                color = self.emphasisColor
                overridecolor = True
            elif i == self.cur_index and self.showSelectionAfterExit:
                color = self.highlightColor
            elif self.colorfun is not None:
                color = self.colorfun(option)
        x = 0
        if self.addBrackets:
            self.layout.window.addstr(y, x, "[", color)
            x += 1
        nchr = option.drawAt(
            y,
            x,
            self.layout,
            color,
            overridecolor=overridecolor,
            renderfun=self.renderfun,
        )
        x += nchr
        if self.addBrackets:
            self.layout.window.addstr(y, x, "]", color)
            x += 1
        nothing = " " * (self._viewWidth - x)
        self.layout.window.addstr(y, x, nothing, self.layout.color.default)
        return x

    def _drawAt_vertical(self, y):
        if y is None:
            return

        my, mx = self.layout.getLayoutSize()
        maxSize = my // 2

        size = 0

        if self.clearBeforeDrawSize > 0:
            if self.clearBeforeDrawSize > maxSize:
                self.clearBeforeDrawSize = maxSize
            nothing = " " * self._getViewWidth()
            for i in range(self.clearBeforeDrawSize):
                self.layout.window.addstr(y + i, 0, nothing, self.layout.color.default)
            self.clearBeforeDrawSize = 0

        def _calc_layout():
            correctedMaxSize = maxSize
            haveMoreAtFront = False
            if self.offset > 0:
                haveMoreAtFront = True
                correctedMaxSize -= 1
            haveMoreAtEnd = False
            if len(self.options) - self.offset > maxSize:
                haveMoreAtEnd = True
                correctedMaxSize -= 1
            return haveMoreAtFront, haveMoreAtEnd, correctedMaxSize

        haveMoreAtFront, haveMoreAtEnd, correctedMaxSize = _calc_layout()
        if self.cur_index is not None:
            prev_offset = -1
            while prev_offset != self.offset:
                prev_offset = self.offset
                if self.cur_index < self.offset:
                    self.offset = self.cur_index
                elif self.cur_index >= self.offset + correctedMaxSize:
                    self.offset = self.cur_index - correctedMaxSize + 1
                if self.offset == 1:
                    self.offset = 2
                (haveMoreAtFront, haveMoreAtEnd, correctedMaxSize) = _calc_layout()

        if haveMoreAtFront:
            entry = TextElement(f"-- {self.offset} more --", self.layout.color.default)
            nchr = self._draw_text(y + size, entry, self.color)
            if nchr > self._viewWidth:
                self._viewWidth = nchr
            size += 1

        upper = self.offset + correctedMaxSize
        if upper > len(self.options):
            upper = len(self.options)
        for i in range(self.offset, upper):
            nchr = self._draw_option(i, y + size)
            if nchr is None:
                continue
            if nchr > self._viewWidth:
                self._viewWidth = nchr
            size += 1

        if haveMoreAtEnd:
            n = len(self.options) - (self.offset + correctedMaxSize)
            entry = TextElement(f"-- {n} more --", self.layout.color.default)
            nchr = self._draw_text(y + size, entry, self.color)
            if nchr > self._viewWidth:
                self._viewWidth = nchr
            size += 1

        return size

    def drawAt(self, y):
        if self.isVertical:
            return self._drawAt_vertical(y)
        else:
            return self._drawAt_horizontal(y)


class MultipleChoiceInputView(SingleChoiceInputView):
    nchr_prepend = 4

    def __init__(self, options, checked=[], isVertical=False, **kwargs):
        super(MultipleChoiceInputView, self).__init__(
            options,
            isVertical=isVertical,
            addBrackets=False,
            showSelectionAfterExit=False,
            renderfun=self._render_option,
            colorfun=self._color_option,
            **kwargs,
        )
        self.checked = {str(k): (str(k) in checked) for k in self.options}

    def _before_call(self):
        if self.cur_index is None:
            self.cur_index = 0
        arrows = "← →"
        if self.isVertical:
            arrows = "↑ ↓"
        self._setStatusBar(
            "  ".join(
                [
                    "[↵] Ok",
                    "[space] Toggle checked/unchecked",
                    f"[{arrows}] Change selection",
                    "[ctrl-c] Cancel",
                ]
            )
        )

    def _handleKey(self, c):
        if c == ord(" "):
            if self.cur_index is not None:
                optionStr = str(self.options[self.cur_index])
                self.checked[optionStr] = not self.checked[optionStr]
                self.update()
        else:
            super(MultipleChoiceInputView, self)._handleKey(c)

    def _getOutput(self):
        if self.cur_index is not None:
            return self.checked

    def _render_option(self, optionStr):
        status = " "
        if self.checked[optionStr]:
            status = "*"
        return f"[{status}] {optionStr}"

    def _color_option(self, option):
        if self.checked[str(option)]:
            return self.highlightColor
        return self.color


class CombinedMultipleAndSingleChoiceInputView(MultipleChoiceInputView):
    def __init__(self, multiple_choice_options, single_choice_options, **kwargs):
        options = [*multiple_choice_options, *single_choice_options]
        self.single_choice_options = single_choice_options
        super(CombinedMultipleAndSingleChoiceInputView, self).__init__(
            options,
            **kwargs,
        )

    def _before_call(self):
        if self.cur_index is None:
            self.cur_index = 0
        arrows = "← →"
        if self.isVertical:
            arrows = "↑ ↓"
        self._setStatusBar(
            "  ".join(
                [
                    "[↵] Ok",
                    "[space] Toggle checked/unchecked",
                    f"[{arrows}] Change selection",
                    "[ctrl-c] Cancel",
                ]
            )
        )

    def _handleKey(self, c):
        if c == ord(" "):
            if self.cur_index is not None:
                optionStr = str(self.options[self.cur_index])
                self.checked[optionStr] = not self.checked[optionStr]
                self.update()
        else:
            super(MultipleChoiceInputView, self)._handleKey(c)

    def _getOutput(self):
        if self.cur_index is not None:
            optionStr = str(self.options[self.cur_index])
            if optionStr in self.single_choice_options:
                return optionStr
            else:
                return {
                    k: v
                    for k, v in self.checked.items()
                    if k not in self.single_choice_options
                }

    def _render_option(self, optionStr):
        if optionStr in self.single_choice_options:
            return f"[{optionStr}]"
        status = " "
        if self.checked[optionStr]:
            status = "*"
        return f"[{status}] {optionStr}"

    def _color_option(self, option):
        if self.checked[str(option)]:
            return self.highlightColor
        return self.color


class MultiSingleChoiceInputView(SingleChoiceInputView):
    def __init__(
        self, options, values, selectedIndices=None, addBrackets=True, **kwargs
    ):
        super().__init__(
            options,
            isVertical=True,
            addBrackets=False,
            showSelectionAfterExit=False,
            **kwargs,
        )
        self.selectedIndices = selectedIndices
        self.optionWidth = max(len(option) for option in options)
        self._add_brackets = addBrackets

        if not isinstance(values[0], list):
            values = [values for _ in options]

        for i in range(len(options)):
            for j in range(len(values[i])):
                if not isinstance(values[i][j], Text):
                    values[i][j] = TextElement(values[i][j])
        self.values = values

    def _before_call(self):
        super(MultiSingleChoiceInputView, self)._before_call()
        if self.selectedIndices is None:
            self.selectedIndices = [0] * len(self.options)
        actions = ["[↵] Ok", "[↑ ↓ ← →] Change selection", "[ctrl-c] Cancel"]
        self._setStatusBar("  ".join(actions))

    def _handleKey(self, c):
        if c == Key.Break:
            self.cur_index = None
            self.selectedIndices = None
            self.isActive = False
        elif c == Key.Left:
            if self.cur_index is not None and self.selectedIndices is not None:
                self.selectedIndices[self.cur_index] = max(
                    0, self.selectedIndices[self.cur_index] - 1
                )
            self.update()
        elif c == Key.Right:
            if self.cur_index is not None and self.selectedIndices is not None:
                self.selectedIndices[self.cur_index] = min(
                    len(self.values[self.cur_index]) - 1,
                    self.selectedIndices[self.cur_index] + 1,
                )
            self.update()
        else:
            super(MultiSingleChoiceInputView, self)._handleKey(c)

    def _getOutput(self):
        if self.selectedIndices is not None:
            return {
                str(k): str(self.values[i][v])
                for i, (k, v) in enumerate(zip(self.options, self.selectedIndices))
            }

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        option.drawAt(y, 0, self.layout, color)
        x += self.optionWidth
        x += 1

        for j, value in enumerate(self.values[i]):
            color = self.color
            if self.selectedIndices is not None:
                if j == self.selectedIndices[i]:
                    if (
                        self.cur_index is not None
                        and i == self.cur_index
                        and self.isActive
                    ):
                        color = self.emphasisColor
                    else:
                        color = self.highlightColor
            if self._add_brackets:
                self.layout.window.addstr(y, x, "[", color)
                x += 1
            nchr = value.drawAt(y, x, self.layout, color)
            x += nchr
            if self._add_brackets:
                self.layout.window.addstr(y, x, "]", color)
                x += 1
            x += 1

        return x


class MultiMultipleChoiceInputView(MultiSingleChoiceInputView):
    nchr_prepend = 4

    def __init__(self, options, values, checked=None, enforce_unique=False, **kwargs):
        super(MultiMultipleChoiceInputView, self).__init__(
            options,
            values,
            addBrackets=False,
            **kwargs,
        )

        self.cur_col = None

        if checked is None:
            checked = [[] for _ in options]
        self.checked: List[Dict[str, bool]] = [
            {str(k): (str(k) in checked[i]) for k in self.values[i]}
            for i in range(len(options))
        ]

        self.enforce_unique = enforce_unique

    def _before_call(self):
        super(MultiSingleChoiceInputView, self)._before_call()
        if self.cur_col is None:
            self.cur_col = 0
        actions = [
            "[↵] Ok",
            "[space] Toggle checked/unchecked",
            "[↑ ↓ ← →] Change selection",
            "[ctrl-c] Cancel",
        ]
        self._setStatusBar("  ".join(actions))

    def _handleKey(self, c):
        if c == Key.Left:
            if self.cur_col is not None:
                self.cur_col = max(0, self.cur_col - 1)
            self.update()
        elif c == Key.Right:
            if self.cur_col is not None:
                self.cur_col = min(
                    len(self.values[self.cur_index]) - 1, self.cur_col + 1
                )
            self.update()
        elif c == ord(" "):
            if self.cur_index is not None and self.cur_col is not None:
                value = str(self.values[self.cur_index][self.cur_col])
                checked = self.checked[self.cur_index][value]
                if not checked and self.enforce_unique:
                    for row in self.checked:
                        if value in row:
                            row[value] = False  # disable other active
                self.checked[self.cur_index][value] = not checked  # toggle value
                self.update()
        else:
            super(MultiSingleChoiceInputView, self)._handleKey(c)

    def _getOutput(self) -> Optional[List[Dict[str, bool]]]:
        if self.cur_index is not None:
            return self.checked
        return None

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        option.drawAt(y, 0, self.layout, color)
        x += self.optionWidth
        x += 1

        for j, value in enumerate(self.values[i]):
            valueStr = str(value)
            checked = self.checked[i][valueStr]
            color = self.color
            if (
                self.cur_col is not None
                and j == self.cur_col
                and self.cur_index is not None
                and i == self.cur_index
                and self.isActive
            ):
                color = self.emphasisColor
            elif checked:
                color = self.highlightColor
            box = "[ ] "
            if checked:
                box = "[*] "
            self.layout.window.addstr(y, x, box, color)
            x += len(box)
            nchr = value.drawAt(y, x, self.layout, color)
            x += nchr
            x += 1

        return x
