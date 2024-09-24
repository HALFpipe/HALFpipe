# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Select, Static, Switch

from .custom_switch import TextSwitch


class SwitchWithInputBox(Widget):
    value: reactive[bool] = reactive(None, init="")
    switch_value: reactive[bool] = reactive(None, init=False)

    @dataclass
    class Changed(Message):
        switch_with_input_box: "SwitchWithInputBox"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_input_box

    @dataclass
    class SwitchChanged(Message):
        switch_with_select: "SwitchWithInputBox"
        switch_value: bool

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_input_box

    def __init__(self, label="", value: str | None = None, switch_value: bool = False, **kwargs) -> None:
        self.label = label
        self._reactive_switch_value = switch_value
        self._reactive_value = str(value) if value is not None else None

        super().__init__(**kwargs)

    def watch_value(self) -> None:
        self.post_message(self.Changed(self, self.value))

    def watch_switch_value(self) -> None:
        self.post_message(self.SwitchChanged(self, self.switch_value))

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            TextSwitch(value=self.value is not None),
            Input(value=self.value, placeholder="Value", id="input_switch_input_box"),
        )

    def update_label(self, label):
        self.query_one(Static).update(label)

    def on_mount(self):
        if self.switch_value is True or self.value is not None:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
        else:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"

    # def on_switch_changed(self):
    # last_switch = self.query("Switch").last()
    # if last_switch.value:
    # self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
    # else:
    # self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"
    # self.value = 0

    @on(Switch.Changed)
    def on_switch_changed(self, message):
        self.switch_value = message.value
        if self.switch_value is True:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
        else:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"

    @on(Input.Changed, "#input_switch_input_box")
    def update_from_input(self):
        self.value = str(self.get_widget_by_id("input_switch_input_box").value)


class SwitchWithSelect(SwitchWithInputBox):
    @dataclass
    class Changed(Message):
        switch_with_select: "SwitchWithSelect"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_select

    @dataclass
    class SwitchChanged(Message):
        switch_with_select: "SwitchWithSelect"
        switch_value: bool

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_select

    def __init__(self, label="", options: list | None = None, **kwargs) -> None:
        self.label = label
        super().__init__(label=label, **kwargs)
        self.options = [] if options is None else options

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            TextSwitch(value=self.switch_value),
            Select(
                [(str(value[0]), value[1]) for value in self.options],
                value=self.options[0][1],
                allow_blank=False,
                id="input_switch_input_box",
            ),
        )

    @on(Select.Changed, "#input_switch_input_box")
    def update_from_input(self):
        self.value = str(self.get_widget_by_id("input_switch_input_box").value)


class LabelWithInputBox(Widget):
    value: reactive[bool] = reactive(None, init="")

    @dataclass
    class Changed(Message):
        label_with_input_box: "LabelWithInputBox"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.label_with_input_box

    def __init__(self, label="", value: str | None = None, **kwargs) -> None:
        self.label = label
        self._reactive_value = str(value) if value is not None else None
        super().__init__(**kwargs)

    def watch_value(self) -> None:
        self.post_message(self.Changed(self, self.value))

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            Input(value=self.value, placeholder="Value", id="input_label_input_box"),
        )

    def update_label(self, label):
        self.query_one(Static).update(label)

    @on(Input.Changed, "#input_label_input_box")
    def update_from_input(self):
        self.value = str(self.get_widget_by_id("input_label_input_box").value)
