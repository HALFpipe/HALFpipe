# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..keyboard import Key
from ..text import Text, TextElement
from ..view import CallableView


class SingleChoiceInputView(CallableView):
    def __init__(
        self,
        options,
        label=None,
        cur_index=None,
        is_vertical=False,
        add_brackets=True,
        show_selection_after_exit=True,
        renderfun=None,
        colorfun=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.is_vertical = is_vertical
        self.add_brackets = add_brackets
        self.show_selection_after_exit = show_selection_after_exit

        self.cur_index: int | None = cur_index

        self.clear_before_draw_size = 0
        self.offset = 0
        self.renderfun = renderfun
        self.colorfun = colorfun

        self.label = label
        self.options: list = list()
        self.set_options(options)

    def set_options(self, newoptions):
        self.offset = 0
        for i in range(len(newoptions)):
            if not isinstance(newoptions[i], Text):
                newoptions[i] = TextElement(newoptions[i])
        if self.options is not None:
            self.clear_before_draw_size = max(self.clear_before_draw_size, len(self.options))
        self.options = newoptions
        if self.cur_index is not None and self.cur_index > len(newoptions):
            self.cur_index = 0

    def _is_ok(self):
        return True

    def _before_call(self):
        if self.cur_index is None:
            self.cur_index = 0
        arrows = "← →"
        if self.is_vertical:
            arrows = "↑ ↓"
        self._set_status_bar("  ".join(["[↵] Ok", f"[{arrows}] Change selection", "[ctrl-c] Cancel"]))

    def _handle_key(self, c):
        if c == Key.Break:
            self.cur_index = None
            self.update()
            self.is_active = False
        elif c == Key.Return:
            if self._is_ok():
                self.is_active = False
        elif (self.is_vertical and c == Key.Up) or (not self.is_vertical and c == Key.Left):
            if self.cur_index is None:
                return
            self.cur_index = max(0, self.cur_index - 1)
            self.update()
        elif (self.is_vertical and c == Key.Down) or (not self.is_vertical and c == Key.Right) or c == Key.Tab:
            if self.cur_index is None:
                return
            self.cur_index = min(len(self.options) - 1, self.cur_index + 1)
            self.update()
        elif isinstance(c, Key):
            pass
        else:
            pass

    def _get_output(self):
        if self.cur_index is not None:
            return str(self.options[self.cur_index])

    def _draw_at_horizontal(self, y):
        if y is None:
            return
        x: int = 0
        if self.label is not None:
            self.layout.window.addstr(y, x, self.label, self.color)
            x += len(self.label)
            x += 1
        for i, option in enumerate(self.options):
            color = self.color
            if i == self.cur_index:
                if self.is_active:
                    color = self.emphasis_color
                elif self.show_selection_after_exit:
                    color = self.highlight_color
            if self.add_brackets:
                self.layout.window.addstr(y, x, "[", color)
                x += 1
            nchr = option.draw_at(y, x, self.layout, color, renderfun=self.renderfun)
            x += nchr
            if self.add_brackets:
                self.layout.window.addstr(y, x, "]", color)
                x += 1
            x += 1

        if x > self._view_width:
            self._view_width = x

        return 1

    def _draw_text(self, y, text, color):
        nchr = text.draw_at(y, 0, self.layout, color)
        nothing = " " * (self._view_width - nchr)
        self.layout.window.addstr(y, nchr, nothing, self.layout.color.default)
        return nchr

    def _draw_option(self, i, y):
        if y is None:
            return
        if i >= len(self.options):
            nothing = " " * self._view_width
            self.layout.window.addstr(y, 0, nothing, self.layout.color.default)
            return
        option = self.options[i]
        color = self.color
        overridecolor = False
        if self.cur_index is not None:
            if i == self.cur_index and self.is_active:
                color = self.emphasis_color
                overridecolor = True
            elif i == self.cur_index and self.show_selection_after_exit:
                color = self.highlight_color
            elif self.colorfun is not None:
                color = self.colorfun(option)
        x = 0
        if self.add_brackets:
            self.layout.window.addstr(y, x, "[", color)
            x += 1
        nchr = option.draw_at(
            y,
            x,
            self.layout,
            color,
            overridecolor=overridecolor,
            renderfun=self.renderfun,
        )
        x += nchr
        if self.add_brackets:
            self.layout.window.addstr(y, x, "]", color)
            x += 1
        nothing = " " * (self._view_width - x)
        self.layout.window.addstr(y, x, nothing, self.layout.color.default)
        return x

    def _draw_at_vertical(self, y):
        if y is None:
            return

        my, mx = self.layout.get_layout_size()
        max_size = my // 2

        size = 0

        if self.clear_before_draw_size > 0:
            if self.clear_before_draw_size > max_size:
                self.clear_before_draw_size = max_size
            nothing = " " * self._get_view_width()
            for i in range(self.clear_before_draw_size):
                self.layout.window.addstr(y + i, 0, nothing, self.layout.color.default)
            self.clear_before_draw_size = 0

        def _calc_layout():
            corrected_max_size = max_size
            have_more_at_front = False
            if self.offset > 0:
                have_more_at_front = True
                corrected_max_size -= 1
            have_more_at_end = False
            if len(self.options) - self.offset > max_size:
                have_more_at_end = True
                corrected_max_size -= 1
            return have_more_at_front, have_more_at_end, corrected_max_size

        have_more_at_front, have_more_at_end, corrected_max_size = _calc_layout()
        if self.cur_index is not None:
            prev_offset = -1
            while prev_offset != self.offset:
                prev_offset = self.offset
                if self.cur_index < self.offset:
                    self.offset = self.cur_index
                elif self.cur_index >= self.offset + corrected_max_size:
                    self.offset = self.cur_index - corrected_max_size + 1
                if self.offset == 1:
                    self.offset = 2
                (have_more_at_front, have_more_at_end, corrected_max_size) = _calc_layout()

        if have_more_at_front:
            entry = TextElement(f"-- {self.offset} more --", self.layout.color.default)
            nchr = self._draw_text(y + size, entry, self.color)
            if nchr > self._view_width:
                self._view_width = nchr
            size += 1

        upper = self.offset + corrected_max_size
        if upper > len(self.options):
            upper = len(self.options)
        for i in range(self.offset, upper):
            nchr = self._draw_option(i, y + size)
            if nchr is None:
                continue
            if nchr > self._view_width:
                self._view_width = nchr
            size += 1

        if have_more_at_end:
            n = len(self.options) - (self.offset + corrected_max_size)
            entry = TextElement(f"-- {n} more --", self.layout.color.default)
            nchr = self._draw_text(y + size, entry, self.color)
            if nchr > self._view_width:
                self._view_width = nchr
            size += 1

        return size

    def draw_at(self, y):
        if self.is_vertical:
            return self._draw_at_vertical(y)
        else:
            return self._draw_at_horizontal(y)


class MultipleChoiceInputView(SingleChoiceInputView):
    nchr_prepend = 4

    def __init__(self, options, checked: list[str] | None = None, is_vertical=False, **kwargs):
        super(MultipleChoiceInputView, self).__init__(
            options,
            is_vertical=is_vertical,
            add_brackets=False,
            show_selection_after_exit=False,
            renderfun=self._render_option,
            colorfun=self._color_option,
            **kwargs,
        )
        if checked is None:
            checked = list()
        self.checked = {str(k): (str(k) in checked) for k in self.options}

    def _before_call(self):
        if self.cur_index is None:
            self.cur_index = 0
        arrows = "← →"
        if self.is_vertical:
            arrows = "↑ ↓"
        self._set_status_bar(
            "  ".join(
                [
                    "[↵] Ok",
                    "[space] Toggle checked/unchecked",
                    f"[{arrows}] Change selection",
                    "[ctrl-c] Cancel",
                ]
            )
        )

    def _handle_key(self, c):
        if c == ord(" "):
            if self.cur_index is not None:
                option_str = str(self.options[self.cur_index])
                self.checked[option_str] = not self.checked[option_str]
                self.update()
        else:
            super(MultipleChoiceInputView, self)._handle_key(c)

    def _get_output(self):
        if self.cur_index is not None:
            return self.checked

    def _render_option(self, option_str):
        status = " "
        if self.checked[option_str]:
            status = "*"
        return f"[{status}] {option_str}"

    def _color_option(self, option):
        if self.checked[str(option)]:
            return self.highlight_color
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
        if self.is_vertical:
            arrows = "↑ ↓"
        self._set_status_bar(
            "  ".join(
                [
                    "[↵] Ok",
                    "[space] Toggle checked/unchecked",
                    f"[{arrows}] Change selection",
                    "[ctrl-c] Cancel",
                ]
            )
        )

    def _handle_key(self, c):
        if c == ord(" "):
            if self.cur_index is not None:
                option_str = str(self.options[self.cur_index])
                self.checked[option_str] = not self.checked[option_str]
                self.update()
        else:
            super(MultipleChoiceInputView, self)._handle_key(c)

    def _get_output(self):
        if self.cur_index is not None:
            option_str = str(self.options[self.cur_index])
            if option_str in self.single_choice_options:
                return option_str
            else:
                return {k: v for k, v in self.checked.items() if k not in self.single_choice_options}

    def _render_option(self, option_str):
        if option_str in self.single_choice_options:
            return f"[{option_str}]"
        status = " "
        if self.checked[option_str]:
            status = "*"
        return f"[{status}] {option_str}"

    def _color_option(self, option):
        if self.checked[str(option)]:
            return self.highlight_color
        return self.color


class MultiSingleChoiceInputView(SingleChoiceInputView):
    def __init__(self, options, values, selected_indices=None, add_brackets=True, **kwargs):
        super().__init__(
            options,
            is_vertical=True,
            add_brackets=False,
            show_selection_after_exit=False,
            **kwargs,
        )
        self.selected_indices = selected_indices
        self.option_width = max(len(option) for option in options)
        self._add_brackets = add_brackets

        if not isinstance(values[0], list):
            values = [values for _ in options]

        for i in range(len(options)):
            for j in range(len(values[i])):
                if not isinstance(values[i][j], Text):
                    values[i][j] = TextElement(values[i][j])
        self.values = values

    def _before_call(self):
        super(MultiSingleChoiceInputView, self)._before_call()
        if self.selected_indices is None:
            self.selected_indices = [0] * len(self.options)
        actions = ["[↵] Ok", "[↑ ↓ ← →] Change selection", "[ctrl-c] Cancel"]
        self._set_status_bar("  ".join(actions))

    def _handle_key(self, c):
        if c == Key.Break:
            self.cur_index = None
            self.selected_indices = None
            self.is_active = False
        elif c == Key.Left:
            if self.cur_index is not None and self.selected_indices is not None:
                self.selected_indices[self.cur_index] = max(0, self.selected_indices[self.cur_index] - 1)
            self.update()
        elif c == Key.Right:
            if self.cur_index is not None and self.selected_indices is not None:
                self.selected_indices[self.cur_index] = min(
                    len(self.values[self.cur_index]) - 1,
                    self.selected_indices[self.cur_index] + 1,
                )
            self.update()
        else:
            super(MultiSingleChoiceInputView, self)._handle_key(c)

    def _get_output(self):
        if self.selected_indices is not None:
            return {
                str(k): str(self.values[i][v])
                for i, (k, v) in enumerate(zip(self.options, self.selected_indices, strict=False))
            }

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        option.draw_at(y, 0, self.layout, color)
        x += self.option_width
        x += 1

        for j, value in enumerate(self.values[i]):
            color = self.color
            if self.selected_indices is not None:
                if j == self.selected_indices[i]:
                    if self.cur_index is not None and i == self.cur_index and self.is_active:
                        color = self.emphasis_color
                    else:
                        color = self.highlight_color
            if self._add_brackets:
                self.layout.window.addstr(y, x, "[", color)
                x += 1
            nchr = value.draw_at(y, x, self.layout, color)
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
            add_brackets=False,
            **kwargs,
        )

        self.cur_col = None

        if checked is None:
            checked = [[] for _ in options]
        self.checked: list[dict[str, bool]] = [
            {str(k): (str(k) in checked[i]) for k in self.values[i]} for i in range(len(options))
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
        self._set_status_bar("  ".join(actions))

    def _handle_key(self, c):
        if c == Key.Left:
            if self.cur_col is not None:
                self.cur_col = max(0, self.cur_col - 1)
            self.update()
        elif c == Key.Right:
            if self.cur_col is not None:
                self.cur_col = min(len(self.values[self.cur_index]) - 1, self.cur_col + 1)
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
            super(MultiSingleChoiceInputView, self)._handle_key(c)

    def _get_output(self) -> list[dict[str, bool]] | None:
        if self.cur_index is not None:
            return self.checked
        return None

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        option.draw_at(y, 0, self.layout, color)
        x += self.option_width
        x += 1

        for j, value in enumerate(self.values[i]):
            value_str = str(value)
            checked = self.checked[i][value_str]
            color = self.color
            if (
                self.cur_col is not None
                and j == self.cur_col
                and self.cur_index is not None
                and i == self.cur_index
                and self.is_active
            ):
                color = self.emphasis_color
            elif checked:
                color = self.highlight_color
            box = "[ ] "
            if checked:
                box = "[*] "
            self.layout.window.addstr(y, x, box, color)
            x += len(box)
            nchr = value.draw_at(y, x, self.layout, color)
            x += nchr
            x += 1

        return x
