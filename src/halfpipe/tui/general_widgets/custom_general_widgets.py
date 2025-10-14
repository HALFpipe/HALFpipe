# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Label, Select, Static, Switch

# from .confirm_screen import Confirm
from .custom_switch import TextSwitch


class SwitchWithInputBox(Widget):
    """
    Combines a Static, TextSwitch, and Input widgets.

    This widget integrates a text input box and a toggle switch, allowing
    for dynamic UI updates based on the switch's state and the input
    value. The input box's visibility is controlled by the switch. The Static
    widget is used for description.

    Attributes
    ----------
    value : reactive[str]
        The reactive value associated with the input box. Changes to this
        value will trigger a `Changed` message.
    switch_value : reactive[bool]
        The reactive value associated with the switch. Changes to this
        value will trigger a `SwitchChanged` message.
    label : str
        The label displayed next to the switch and input box.

    Events
    ------
    Changed
        Posted when the input box value changes.
    SwitchChanged
        Posted when the switch value changes.

    Methods
    -------
    __init__(label, value, switch_value, id, classes)
        Initializes the widget with a label, input value, and switch state.
    watch_value()
        Posts a `Changed` message when the input value changes.
    watch_switch_value()
        Posts a `SwitchChanged` message when the switch value changes.
    compose() -> ComposeResult
        Composes and yields the widget components (label, switch, input box).
    update_label(label)
        Updates the label component of the widget.
    update_value(value)
        Updates the value of the input box.
    update_switch_value(value)
        Updates the value of the switch.
    on_mount()
        Configures the visibility of the input box based on the initial
        switch value.
    on_switch_changed(message)
        Handles the `Switch.Changed` event to update the switch value and
        input box visibility.
    update_from_input()
        Updates the widget's input value based on changes in the input box.
    """

    value: reactive[str] = reactive(None, init=False)
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
        switch_with_input_box: "SwitchWithInputBox"
        switch_value: bool

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_input_box

    def __init__(
        self, label="", value: str | None = None, switch_value: bool = True, id: str | None = None, classes: str | None = None
    ) -> None:
        """
        Initializes the SwitchWithInputBox widget.

        Parameters
        ----------
        label : str, optional
            The label to display next to the switch and input box,
            by default "".
        value : str | None, optional
            The initial value of the input box, by default None.
        switch_value : bool, optional
            The initial state of the switch (True for on, False for off),
            by default True.
        id : str | None, optional
            The ID of the widget, by default None.
        classes : str | None, optional
            CSS classes for the widget, by default None.
        """
        self.label = label
        self._reactive_switch_value = switch_value
        self._reactive_value = str(value) if value is not None else None

        super().__init__(id=id, classes=classes)

    def watch_value(self) -> None:
        """
        Posts a `Changed` message when the input value changes.

        This method is called automatically by Textual when the `value`
        reactive attribute changes.
        """
        self.post_message(self.Changed(self, self.value))

    def watch_switch_value(self) -> None:
        """
        Posts a `SwitchChanged` message when the switch value changes.

        This method is called automatically by Textual when the
        `switch_value` reactive attribute changes.
        """
        self.post_message(self.SwitchChanged(self, self.switch_value))

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            TextSwitch(value=self.switch_value, id="the_switch"),
            Input(value=self.value, placeholder="Value", id="input_switch_input_box"),
        )

    def update_label(self, label):
        self.query_one(Static).update(label)

    def update_value(self, value):
        self.get_widget_by_id("input_switch_input_box").value = value

    def update_switch_value(self, value):
        self.get_widget_by_id("the_switch").value = value

    def on_mount(self):
        """
        Configures the visibility of the input box on mount.

        This method is called when the widget is mounted. It sets the
        visibility of the input box based on the initial `switch_value`.
        """
        if self.switch_value is True:  # or self.value is not None:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
        else:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"

    @on(Switch.Changed)
    def on_switch_changed(self, message):
        self.switch_value = message.value
        if self.switch_value is True:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
        else:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"

    @on(Input.Changed, "#input_switch_input_box")
    def update_from_input(self):
        self.value = self.get_widget_by_id("input_switch_input_box").value

    # def notify_style_update(self) -> None:
    #     # this does not work as expected
    #     # """Ensure all child widgets follow the visibility of the main widget."""
    #     visibility = self.styles.visibility
    #     for widget in self.query("Switch, Input, Static"):
    #         widget.styles.visibility = visibility


class SwitchWithSelect(SwitchWithInputBox):
    """
    Combines a Static, TextSwitch, Select widgets.

    This subclass replaces the inputbox from `SwitchWithInputBox` with a selection list.
    The visibility of the selection list is controlled by the switch, and the selected value
    is stored in the `value` attribute.

    Attributes
    ----------
    value : reactive[str]
        The reactive value associated with the selected item in the
        selection list. Changes to this value will trigger a `Changed`
        message.
    switch_value : reactive[bool]
        The reactive value associated with the switch. Changes to this
        value will trigger a `SwitchChanged` message.
    label : str
        The label displayed next to the switch and selection list.
    options : list[tuple[str, str]]
        A list of tuples, where each tuple contains the display text and
        the internal value for an option in the selection list.
    default_option : str
        The default value to be selected in the selection list.

    Events
    ------
    Changed
        Posted when the selected value in the selection list changes.
    SwitchChanged
        Posted when the switch value changes.

    Methods
    -------
    __init__(label, switch_value, options, default_option, id, classes)
        Initializes the widget with a label, switch state, options, and
        default option.
    compose() -> ComposeResult
        Composes and yields the widget components (label, switch,
        selection list).
    update_from_input()
        Updates the widget's `value` attribute based on changes in the
        selection list.
    """

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

    def __init__(
        self,
        label="",
        switch_value: bool = True,
        options: list | None = None,
        default_option=None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initializes the SwitchWithSelect widget.

        Parameters
        ----------
        label : str, optional
            The label to display next to the switch and selection list,
            by default "".
        switch_value : bool, optional
            The initial state of the switch (True for on, False for off),
            by default True.
        options : list[tuple[str, str]] | None, optional
            A list of tuples, where each tuple contains the display text
            and the internal value for an option in the selection list,
            by default None.
        default_option : str | None, optional
            The default value to be selected in the selection list. If
            None, the first option will be selected, by default None.
        id : str | None, optional
            The ID of the widget, by default None.
        classes : str | None, optional
            CSS classes for the widget, by default None.
        """
        self.label = label
        super().__init__(label=label, id=id, classes=classes)
        self.options = [] if options is None else options
        self.default_option = self.options[0][1] if default_option is None else default_option
        self.switch_value = switch_value
        self.value = self.default_option

    @property
    def selected(self):
        # TODO revisite this after textual update
        return self.query_exactly_one(Select).value

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            TextSwitch(value=self.switch_value, id="the_switch"),
            Select(
                [(str(value[0]), value[1]) for value in self.options],
                value=self.default_option,
                allow_blank=False,
                id="input_switch_input_box",
            ),
        )

    @on(Select.Changed, "#input_switch_input_box")
    def update_from_input(self):
        """
        Updates the widget's `value` attribute based on changes in the selection list.

        This method is called when the selection list's value changes. It
        updates the `value` attribute of the widget.
        """
        self.value = str(self.get_widget_by_id("input_switch_input_box").value)


class LabelWithInputBox(Widget):
    """
    Combines a Static widget with an Input widget.

    This widget integrates a static label with an input box, allowing
    users to enter text. The input box's value is stored in the reactive
    `value` attribute, and changes to this value trigger a `Changed`
    message.

    Attributes
    ----------
    value : reactive[str]
        The reactive value associated with the input box. Changes to this
        value will trigger a `Changed` message.
    label : str
        The label displayed next to the input box.

    Events
    ------
    Changed
        Posted when the input box value changes.

    Methods
    -------
    __init__(label, value, id, classes)
        Initializes the widget with a label and an optional initial value.
    watch_value()
        Posts a `Changed` message when the input value changes.
    compose() -> ComposeResult
        Composes and yields the widget components (label, input box).
    update_label(label)
        Updates the label component of the widget.
    update_from_input()
        Updates the widget's `value` attribute based on changes in the
        input box.
    """

    value: reactive[bool] = reactive(None, init=False)

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
        """
        Updates the widget's `value` attribute based on changes in the input box.

        This method is called when the input box's value changes. It
        updates the `value` attribute of the widget.
        """
        self.value = str(self.get_widget_by_id("input_label_input_box").value)


class LabelledSwitch(Widget):
    """
    Combines a Static and Switch widgets.

    This widget integrates a static label with a `TextSwitch` (a custom
    switch widget), providing a clear description alongside the switch.

    Attributes
    ----------
    value : bool
        The current state of the switch (True for on, False for off).
    label : str
        The label displayed next to the switch.
    help_message : str
        An optional message to provide additional information about the
        switch's purpose.

    Events
    ------
    Changed
        Posted when the switch value changes.

    Methods
    -------
    __init__(label, value, help_message, id)
        Initializes the widget with a label, initial value, help message,
        and an optional ID.
    compose() -> ComposeResult
        Composes and yields the widget components (label, switch).
    update_value(value)
        Updates the value of the switch.
    _on_select(event)
        Handles the `Switch.Changed` event to post a `Changed` message.
    """

    def __init__(self, label, value, help_message="Explain the functionality", id=None):
        """
        Initializes the LabelledSwitch widget.

        Parameters
        ----------
        label : str
            The label to display next to the switch.
        value : bool
            The initial state of the switch (True for on, False for off).
        help_message : str, optional
            An optional message to provide additional information about the
            switch's purpose, by default "Explain the functionality".
        id : str | None, optional
            The ID of the widget, by default None.
        """
        super().__init__(id=id)
        self.label = label
        self.value = value
        self.help_message = help_message

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            TextSwitch(self.value),
        )

    def update_value(self, value):
        self.query_one(Switch).value = value

    @on(Switch.Changed)
    def _on_select(self, event):
        self.post_message(self.Changed(event.value, self))

    @dataclass
    class Changed(Message):
        """Inform ancestor the selection was changed."""

        value: str
        labelled_switch: LabelledSwitch

        @property
        def control(self) -> LabelledSwitch:
            """The Select that sent the message."""
            return self.labelled_switch


class FocusLabel(Label):
    DEFAULT_CSS = """
    FocusLabel {
        padding: 1 1 1 1;
        margin: 0 1;
        width: 100%;
        background: white;
    }
    """

    @dataclass
    class Selected(Message):
        focus_label: "FocusLabel"

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.focus_label

    background = reactive("gray")
    color = reactive("black")

    def __init__(self, text: str, id=None) -> None:
        super().__init__(text, id=id)
        self.can_focus = True  # Make the label focusable
        self.select()

    def watch_background(self, background: str) -> None:
        self.styles.background = background

    def watch_color(self, color: str) -> None:
        self.styles.color = color

    def on_focus(self) -> None:
        self.select()
        self.post_message(self.Selected(self))

    def select(self) -> None:
        self.background = "blue"
        self.color = "white"

    def deselect(self) -> None:
        self.background = "#434C5E"
        self.color = "white"
