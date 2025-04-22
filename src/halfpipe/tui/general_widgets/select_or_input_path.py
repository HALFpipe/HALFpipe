# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass
from typing import Iterable, TypeVar, Union

from rich.console import RenderableType
from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Horizontal

# from textual.keys import _get_key_display
from textual.message import Message
from textual.reactive import var
from textual.widgets import Input, OptionList, Select, Static
from textual.widgets._select import EmptySelectError, NoSelection
from textual.widgets.option_list import Option
from typing_extensions import TypeAlias

SelectType = TypeVar("SelectType")
"""The type used for data in the Select."""
SelectOption: TypeAlias = "tuple[str, SelectType]"
"""The type used for options in the Select."""


def find_common_start(strings):
    """
    Finds the longest common starting substring among a list of strings.

    Parameters
    ----------
    strings : list of str
        A list of strings to find the common starting substring among them.

    Returns
    -------
    str
        The longest common starting substring found in all the input strings.
        If no common start exists, returns an empty string.
    """
    if not strings:
        return ""

    common_start = strings[0]
    for s in strings[1:]:
        # Reduce the common_start while it's not a prefix of s
        while not s.startswith(common_start):
            common_start = common_start[:-1]
            if not common_start:
                return ""
    return common_start


def create_path_option_list(base="/", include_base=False):
    """
    Creates a list of file paths within a specified base directory.

    Parameters
    ----------
    base : str, optional
        The base directory path, default is "/".
    include_base : bool, optional
        Determines whether to include the base directory in the returned list,
        default is False.

    Returns
    -------
    list[str]
        A sorted list of file paths found within the base directory.
    """
    filepaths = [base] if include_base else []
    if os.access(base, os.W_OK):
        for f in os.scandir(base):
            filepath = f.path
            if f.is_dir():
                filepath += "/"
            filepaths.append(filepath)
        filepaths.sort()
    return filepaths


class SelectOverlay(OptionList):
    """
    An overlay for selecting options, extending OptionList.

    This class provides an overlay that displays a list of options,
    allowing the user to select one. It supports dismissing the overlay
    and updating the selection.

    Attributes
    ----------
    BINDINGS : list[tuple[str, str]]
        Key bindings specific for the overlay, such as the escape key to
        dismiss.

    Methods
    -------
    select(index)
        Highlights the option at the given index.
    action_dismiss()
        Dismisses the overlay.
    _on_blur(_event)
        Dismisses the overlay when it loses focus.
    on_option_list_option_selected(event)
        Informs the parent when an option is selected.
    on_key(event)
        Handles key events within the overlay.
    """

    BINDINGS = [("escape", "dismiss")]

    @dataclass
    class Dismiss(Message):
        """Inform ancestor the overlay should be dismissed."""

        lost_focus: bool = False
        """True if the overlay lost focus."""

    @dataclass
    class UpdateSelection(Message):
        """Inform ancestor the selection was changed."""

        option_index: int
        """The index of the new selection."""

    @dataclass
    class Typing(Message):
        """Inform ancestor the overlay should be dismissed."""

        value: str
        """True if the overlay lost focus."""

    def select(self, index: int | None) -> None:
        """Move selection.

        Args:
            index: Index of new selection.
        """
        self.highlighted = index
        self.scroll_to_highlight(top=True)

    def action_dismiss(self) -> None:
        """Dismiss the overlay."""
        self.post_message(self.Dismiss())

    def on_blur(self, _event: events.Blur) -> None:
        """On blur we want to dismiss the overlay."""
        self.post_message(self.Dismiss(lost_focus=True))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Inform parent when an option is selected."""
        event.stop()
        self.post_message(self.UpdateSelection(event.option_index))

    async def on_key(self, event: events.Key) -> None:
        """This allows to typing in the prompt when the focus is on the overlay."""
        if any(mod in event.key for mod in ["ctrl", "alt", "shift"]):
            return
        # List of specific disallowed keys
        disallowed_keys = [
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "pageup",
            "pagedown",
            "tab",
            "delete",
            "insert",
            "enter",
            "return",
            "space",
            "capslock",
            "numlock",
            "scrolllock",
        ] + [f"F{i}" for i in range(1, 13)]  # Function keys

        if event.key in disallowed_keys:
            # Ignore disallowed keys
            pass
        else:
            # Process allowed keys here
            if event.key == "escape":
                event.stop()
            self.post_message(self.Typing(event.key))


class MyInput(Input):
    """
    A custom input class that allows additional functionality such as shrink.

    This class extends `Input` to provide a customizable input field.

    Parameters
    ----------
    shrink : bool, optional
        If True, enables the shrink property for the input, by default True.
    id : str or None, optional
        An optional identifier for the input instance, by default None.
    classes : str or None, optional
        Additional CSS classes to apply to the input instance, by default None.

    Methods
    -------
    _on_click(event)
        Informs the parent that a click event occurred.
    """

    def __init__(self, shrink: bool = True, id: str | None = None, classes: str | None = None, **kwargs) -> None:
        super().__init__(id=id, classes=classes, **kwargs)
        self.shrink = shrink

    class Toggle(Message):
        """Request toggle overlay."""

    async def _on_click(self, event: events.Click) -> None:
        """Inform ancestor we want to toggle."""
        self.post_message(self.Toggle())


class MyStatic(Static):
    """
    A custom static class that allows additional functionality such as toggle.

    This class extends `Static` to provide a customizable static field.

    Methods
    -------
    _on_click(event)
        Informs the parent that a click event occurred.
    """

    class Toggle(Message):
        """Request toggle overlay."""

    async def _on_click(self, event: events.Click) -> None:
        """Inform ancestor we want to toggle."""
        self.post_message(self.Toggle())


class SelectCurrentWithInput(Horizontal):
    """
    A custom widget that combines Input field and toggle arrows.

    This widget combines an input field (`MyInput`) with static elements
    (`MyStatic`) to create a custom selection interface. It handles
    various user interactions and provides messages for communication.

    Attributes
    ----------
    DEFAULT_CSS : str
        Default CSS styling for the widget.
    has_value : var[bool]
        A flag indicating whether the input field has a value.

    Methods
    -------
    __init__(placeholder, id, classes)
        Initializes the widget with a placeholder, ID, and classes.
    compose() -> ComposeResult
        Composes the widget's components.
    update(new_placeholder)
        Updates the content in the widget.
    on_input_changed(message)
        Handles changes in the input field.
    on_key(event)
        Handles key events.
    _watch_has_value(has_value)
        Toggles the class based on the `has_value` attribute.
    """

    @dataclass
    class PromptChanged(Message):
        """Inform ancestor the selection was changed."""

        value: str

    @dataclass
    class PromptCloseOverlay(Message):
        """Inform ancestor the selection was changed."""

    has_value: var[bool] = var(False)

    class Toggle(Message):
        """Request toggle overlay."""

    def __init__(self, placeholder: str, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the widget with a placeholder, ID, and classes.

        Parameters
        ----------
        placeholder : str
            The placeholder text for the input field.
        id : str | None, optional
            The ID of the widget, by default None.
        classes : str | None, optional
            CSS classes for the widget, by default None.
        """
        super().__init__(id=id, classes=classes)
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield MyInput(name="select_input", placeholder=self.placeholder, id="input_prompt")
        yield MyStatic("▼", classes="arrow down-arrow")
        yield MyStatic("▲", classes="arrow up-arrow")

    def update(self, new_placeholder: RenderableType | NoSelection) -> None:
        """
        Updates the content in the widget.

        Parameters
        ----------
        new_placeholder : RenderableType | NoSelection
            A renderable to display, or `NoSelection` for the placeholder.
        """
        self.new_placeholder = new_placeholder
        # This will change the MyInput widget value also and triggers "on_input_changed"
        self.get_widget_by_id("input_prompt").value = (
            self.placeholder if isinstance(new_placeholder, NoSelection) else new_placeholder
        )

    def on_input_changed(self, message):
        """
        Handles changes in the input field. When user types to prompt this method is triggered.
        when user selects option this method is triggered.

        Parameters
        ----------
        message : Input.Changed
            The message object containing information about the input change.
        """
        path = self.get_widget_by_id("input_prompt").value
        self.post_message(self.PromptChanged(path))

    async def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.post_message(self.PromptCloseOverlay())
            event.stop()

    def _watch_has_value(self, has_value: bool) -> None:
        """Toggle the class."""
        self.set_class(has_value, "-has-value")


class SelectOrInputPath(Select):
    """
    A customizable selection widget that allows users to either select from a list or input a path.

    This class extends `Select` to provide a selection widget that
    combines a list of options with an input field for custom paths.

    Attributes
    ----------
    DEFAULT_CSS : str
        The default CSS styling for the widget.
    expanded : var[bool]
        True to show the overlay, otherwise False.
    prompt : var[str]
        The prompt to show when no value is selected.
    value : var[SelectType | NoSelection]
        The value of the selection.
    input_class : type[SelectCurrentWithInput]
        The class used for the input field.

    Methods
    -------
    __init__(options, prompt_default, top_parent, id, classes)
        Initializes the widget with options, a default prompt, and other
        parameters.
    prepare_compose()
        Prepares the components to be composed.
    compose() -> ComposeResult
        Composes the widget's components.
    _setup_variables_for_options(options)
        Sets up the variables for the options.
    _setup_options_renderables()
        Sets up the Option renderables.
    _init_selected_option(hint)
        Initializes the selected option.
    on_key(event)
        Handles key events.
    _select_current_with_input_prompt_close_overlay(event)
        Handles the event when the overlay is closed.
    _select_current_with_input_prompt_changed(event)
        Handles changes in the input prompt.
    _update_selection(event)
        Updates the current selection.
    _select_overlay_typing(event)
        Passes the typing activity on overlay to the main widget.
    _my_input_toggle(event)
        Handles the toggle event from MyInput.
    _my_static_toggle(event)
        Handles the toggle event from MyStatic.
    _watch_value(value)
        Updates the current value when it changes.
    _watch_expanded(expanded)
        Displays or hides the overlay.
    _watch_prompt(prompt)
        Handles changes in the prompt.
    action_show_overlay()
        Shows the overlay.
    _validate_value(value)
        Validates the value.
    change_prompt_from_parrent(new_value)
        Changes the prompt.
    """

    expanded: var[bool] = var(False, init=False)
    """True to show the overlay, otherwise False."""
    prompt: var[str] = var[str]("Select")
    """The prompt to show when no value is selected."""
    value: var[SelectType | NoSelection] = var[Union[SelectType, NoSelection]]("")
    """The value of the selection."""

    input_class = SelectCurrentWithInput

    @dataclass
    class PromptChanged(Message):
        """Inform ancestor the selection was changed."""

        value: str

    def __init__(self, options, *, prompt_default: str = "", top_parent=None, id=None, classes=None):
        """
        Initializes the SelectOrInputPath widget.

        Parameters
        ----------
        options : Iterable[tuple[RenderableType, SelectType]]
            An iterable of tuples, where each tuple contains a renderable
            prompt and a value.
        prompt_default : str, optional
            The default prompt to display when no value is selected,
            by default "".
        top_parent : Widget | None, optional
            The parent widget, by default None.
        id : str | None, optional
            The ID of the widget, by default None.
        classes : str | None, optional
            CSS classes for the widget, by default None.
        """
        # pass default as prompt to super since this will be used as an fixed option in the optionlist
        super().__init__(options, prompt=prompt_default, id=id, classes=classes)
        self.top_parent = top_parent
        self._value: str = prompt_default
        self.prompt_default = prompt_default
        self._setup_variables_for_options(options)

    def prepare_compose(self):
        yield self.input_class(self._value)
        yield SelectOverlay()

    @on(SelectOverlay.Dismiss)
    def on_select_overlay_dismiss(self, event: SelectOverlay.Dismiss):
        event.stop()
        self.expanded = not self.expanded

    def compose(self) -> ComposeResult:
        # Collect results from prepare_compose
        for widget in self.prepare_compose():
            yield widget

    def _setup_variables_for_options(
        self,
        options: Iterable[tuple[RenderableType, SelectType]],
    ) -> None:
        """
        Sets up the variables for the options.

        This method initializes the `_options` and `_legal_values` attributes based on the provided options.

        Parameters
        ----------
        options : Iterable[tuple[RenderableType, SelectType]]
            An iterable of tuples, where each tuple contains a renderable prompt and a value.

        Raises
        ------
        EmptySelectError
            If the options list is empty and blank selection is not allowed.
        """
        self._options: list[tuple[RenderableType, SelectType | NoSelection]] = []
        self._options.extend(options)

        if not self._options:
            raise EmptySelectError("Select options cannot be empty if selection can't be blank.")

        self._legal_values: set[SelectType | NoSelection] = {value for _, value in self._options}

    def _setup_options_renderables(self) -> None:
        """Sets up the `Option` renderables associated with the `Select` options.

        This method creates `Option` instances for each option and adds them to the `SelectOverlay`.
        """
        # if _allow_blank is true, then the self.BLANK is appended and here we use it to put the default into the options
        self._select_options: list[Option] = [
            (Option(Text(self.prompt_default, style="dim")) if value == self.prompt_default else Option(prompt))
            for prompt, value in self._options
        ]

        option_list = self.query_one(SelectOverlay)
        option_list.clear_options()
        for option in self._select_options:
            option_list.add_option(option)

    def _init_selected_option(self, hint) -> None:
        """Initialises the selected option for the `Select`.

        Parameters
        ----------
        hint : SelectType
            The value to select.
        """
        # If allow_blank then no default is available and use first option in the list
        if hint == "" and self._allow_blank:
            hint = self._options[0][1]
        self.value = hint

    async def on_key(self, event: events.Key) -> None:
        """
        Handles key events within the widget.

        This method handles key presses for path suggestions, closing the overlay, and opening the overlay.

        Parameters
        ----------
        event : events.Key
            The key event.
        """
        # Path suggestions
        if event.key == "shift+right":
            select_current = self.query_one(self.input_class)
            myinput = select_current.get_widget_by_id("label")
            current_path = myinput.value
            strings = (
                create_path_option_list(current_path.rsplit("/", 1)[0])
                if current_path.count("/") > 1
                else create_path_option_list("/")
            )
            strings = [f for f in strings if current_path in f]
            myinput.value = find_common_start(strings)
            myinput.cursor_position = len(myinput.value)
        # Close the overlay.
        select_overlay = self.query_one(SelectOverlay)
        if event.key == "esc" and self.expanded is True:
            self.expanded = False
        # Opens the overlay.
        if event.key == "down":
            self.expanded = True
            select_overlay.focus()

    @on(input_class.PromptCloseOverlay)
    def _select_current_with_input_prompt_close_overlay(self, event: SelectCurrentWithInput.PromptCloseOverlay):
        """
        Handles the event when the overlay is closed.

        This method is called when the `PromptCloseOverlay` message is received from the `SelectCurrentWithInput` widget.
        It ensures that the overlay remains closed.

        Parameters
        ----------
        event : SelectCurrentWithInput.PromptCloseOverlay
            The message object.
        """
        if self.input_class == SelectCurrentWithInput:
            self.expanded = False

    @on(input_class.PromptChanged)
    def _select_current_with_input_prompt_changed(self, event: SelectCurrentWithInput.PromptChanged):
        """
        Handles changes in the input prompt.

        This method is called when the `PromptChanged` message is received from the `SelectCurrentWithInput` widget.
        It updates the widget's value and provides path suggestions based on the user's input.

        Parameters
        ----------
        event : SelectCurrentWithInput.PromptChanged
            The message object.
        """
        if self.input_class == SelectCurrentWithInput:
            path = event.value
            self.value = path
            self.post_message(self.PromptChanged(path))
            if os.path.exists(path):
                if path.endswith("/") and os.path.isdir(path):
                    # When user selects option this is triggered
                    path_suggestions = create_path_option_list(base=path)
                    if path_suggestions != []:
                        self._setup_variables_for_options([(f, f) for f in path_suggestions])
                        self._setup_options_renderables()
            else:
                # When user types to prompt this is triggered
                filepaths = []
                path_uncomplete = path
                path = path.rsplit("/", 1)[0] if path.count("/") > 1 else "/"
                if os.path.exists(path) and os.path.isdir(path):
                    for f in os.scandir(path):
                        filepath = f.path
                        if f.is_dir():
                            filepath += "/"
                        if filepath.startswith(path_uncomplete):
                            filepaths.append(filepath)
                        filepaths.sort()
                    self.expanded = True
                    if filepaths != []:
                        self._setup_variables_for_options([(f, f) for f in filepaths])
                        self._setup_options_renderables()
            if os.path.isfile(path):
                self.expanded = False

    @on(SelectOverlay.UpdateSelection)
    def _update_selection(self, event: SelectOverlay.UpdateSelection) -> None:
        """
        Updates the current selection.

        This method is called when the `UpdateSelection` message is received from the `SelectOverlay` widget.
        It updates the widget's value based on the selected option.

        Parameters
        ----------
        event : SelectOverlay.UpdateSelection
            The message object.
        """
        event.stop()
        value = self._options[event.option_index][1]
        if value != self.value:
            self.value = value
            self.post_message(self.Changed(self, value))

    @on(SelectOverlay.Typing)
    async def _select_overlay_typing(self, event: SelectOverlay.Typing):
        """
        Passes the typing activity on overlay to the main widget and update the path.

        This method is called when the `Typing` message is received from the `SelectOverlay` widget.
        It updates the input field with the typed characters.

        Parameters
        ----------
        event : SelectOverlay.Typing
            The message object.
        """
        select_current = self.query_one(self.input_class)
        #  myinput = select_current.query_one(MyInput)
        myinput = select_current.get_widget_by_id("input_prompt")
        #
        myinput_current_value = myinput.value
        # when we have the selection unrolled and it is focussed, we have 3 different scenarios
        # 1) User presses backspace to delete last latter, here we update the input value accordingly
        if event.value == "backspace":
            myinput.value = myinput_current_value[:-1]
        # 2) User presses escape to close the selection, here we set expanded to False to close it.
        elif event.value == "escape":
            self.expanded = False
        # 3) If a key with letter or number is stroked we expand the input value by it. We identify such keys with their length
        # equal to "1" because other keys such as ctrl, alt and etc return strings made of more letters.
        elif len(event.value) == 1:
            myinput.value = myinput_current_value + event.value
        # '/' is identify as 'slash' so we need to translate it back
        elif event.value == "slash":
            myinput.value = myinput_current_value + "/"

    @on(MyInput.Toggle)
    def _my_input_toggle(self, event: MyInput.Toggle):
        """
        Handles the toggle event from MyInput.

        This method is called when the `Toggle` message is received from the `MyInput` widget.
        It toggles the expanded state of the widget.

        Parameters
        ----------
        event : MyInput.Toggle
            The message object.
        """
        event.stop()
        self.expanded = not self.expanded

    @on(MyStatic.Toggle)
    def _my_static_toggle(self, event: MyStatic.Toggle):
        """
        Handles the toggle event from MyStatic.

        This method is called when the `Toggle` message is received from the `MyStatic` widget.
        It toggles the expanded state of the widget.

        Parameters
        ----------
        event : MyStatic.Toggle
            The message object.
        """
        event.stop()
        self.expanded = not self.expanded

    # this is when a selection is made to update the input (prompt)
    def _watch_value(self, value: SelectType | NoSelection) -> None:
        """
        Updates the current value when it changes.

        This method is called when the `value` reactive attribute changes.
        It updates the input field with the new value and highlights the
        corresponding option in the overlay.

        Parameters
        ----------
        value : SelectType | NoSelection
            The new value.
        """
        # When user selects option this is triggered
        self._value = str(value)
        select_current = self.query_one(self.input_class)
        for index, (_, _value) in enumerate(self._options):
            if _value == value:
                select_overlay = self.query_one(SelectOverlay)
                select_overlay.highlighted = index
                select_current.update(value)
                break
        self.post_message(self.PromptChanged(self.value))

    def _watch_expanded(self, expanded: bool) -> None:
        """
        Displays or hides the overlay.

        This method is called when the `expanded` reactive attribute changes.
        It shows or hides the overlay based on the new value.

        Parameters
        ----------
        expanded : bool
            True to show the overlay, False to hide it.
        """
        # unchanged from the super, except SelectCurrent > self.input_class and no BLANK
        overlay = self.query_one(SelectOverlay)
        self.set_class(expanded, "-expanded")
        select_current = self.query_one(self.input_class)
        if expanded:
            value = self.value
            select_current.has_value = False
            for index, (_prompt, prompt_value) in enumerate(self._options):
                if value == prompt_value:
                    overlay.select(index)
                    break
        else:
            select_current.has_value = True

    def _watch_prompt(self, prompt: str) -> None:
        """
        Handles changes in the prompt.

        This method is called when the `prompt` reactive attribute changes.
        Prompt variable is not used in this child subclass, so we override it to
        do nothing.

        Parameters
        ----------
        prompt : str
            The new prompt value.
        """
        pass

    def action_show_overlay(self) -> None:
        """Show the overlay."""
        # Unchanged from the super, except SelectCurrent > self.input_class and has value is not used here
        self.expanded = True

    def _validate_value(self, value: SelectType | NoSelection) -> SelectType | NoSelection:
        """
        Validates the value.

        This method is called to validate the value before it is set.
        In this implementation, it simply returns the value unchanged.

        Parameters
        ----------
        value : SelectType | NoSelection
            The value to validate.

        Returns
        -------
        SelectType | NoSelection
            The validated value.
        """
        return value

    def change_prompt_from_parrent(self, new_value):
        """
        Changes the prompt from the parent.

        This method is called to change the prompt value from a parent widget.
        It updates the input field with the new value.

        Parameters
        ----------
        new_value : str
            The new prompt value.
        """
        if new_value != "/":
            if os.path.isdir(new_value):
                new_value += "/"

        select_current = self.query_one(self.input_class)
        select_current.update(new_value)
