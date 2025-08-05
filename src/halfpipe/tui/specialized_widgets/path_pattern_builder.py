# -*- coding: utf-8 -*-

import re
from typing import Any

from rich.text import Text
from textual import events, on, work
from textual.containers import Container, Grid, HorizontalScroll
from textual.widgets import Button, Static

from ...ingest.glob import resolve_path_wildcards, tag_glob
from ...logging import logger
from ..data_analyzers.context import ctx
from ..general_widgets.draggable_modal_screen import DraggableModalScreen
from ..general_widgets.list_of_files_modal import ListOfFiles
from ..specialized_widgets.file_browser_modal import FileBrowserModal, path_test_with_isfile_true
from .confirm_screen import Confirm
from .pattern_suggestor import (
    InputWithColoredSuggestions,
    SegmentHighlighting,
    SelectCurrentWithInputAndSegmentHighlighting,
)


# utilities for the widget
def convert_validation_error_to_string(error: Any) -> str:
    """
    Converts a validation error object to a string.

    This function takes a validation error object (typically from a
    library like Marshmallow) and converts it into a human-readable
    string. It extracts the field names and their associated error
    messages and formats them into a single string.

    Parameters
    ----------
    error : Any
        The validation error object.

    Returns
    -------
    str
        A string containing the formatted validation error messages.
    """
    # `error.messages` contains the validation errors as a dictionary
    result = []

    for field, messages in error.messages.items():
        # Join the list of error messages for each field into a single string
        messages_str = ", ".join(messages)
        result.append(f"{field}: {messages_str}")

    # Return all error messages concatenated into a single string, separated by '; '
    return "; ".join(result)


def check_wrapped_tags(path: str, tags: list[str]) -> bool:
    """
    Checks if any of the specified tags are wrapped in curly braces in the given path.

    This function uses a regular expression to search for any of the
    provided tags within curly braces in the input path.

    Parameters
    ----------
    path : str
        The path string to search within.
    tags : list[str]
        A list of tags to search for.

    Returns
    -------
    bool
        True if any of the tags are found wrapped in curly braces,
        False otherwise.
    """
    # Regular expression to check for keywords wrapped in curly braces
    pattern = r"\{(" + "|".join(tags) + r")\}"

    # Search for the pattern in the input string
    match = re.search(pattern, path)

    # Return True if a match is found, otherwise False
    return bool(match)


class ColorButton(Button):
    """
    A button widget that sets the current highlighting color.

    This class extends the `Button` widget to provide a button that,
    when clicked, sets the highlight color of a specified widget.

    Attributes
    ----------
    color : str
        The color associated with the button, used for styling the
        background.

    Methods
    -------
    __init__(color, *args, **kwargs)
        Initializes the ColorButton with a specified color.
    on_click(event)
        Handles the click event and sets the highlight color of a
        specific widget.
    """

    def __init__(self, color: str, *args: Any, **kwargs: Any) -> None:
        """
        Initializes the ColorButton with a specified color.

        Parameters
        ----------
        color : str
            The color associated with the button.
        *args : Any
            Additional positional arguments passed to the base class
            constructor.
        **kwargs : Any
            Additional keyword arguments passed to the base class
            constructor.
        """
        super().__init__(*args, **kwargs)
        self.color = color
        self.styles.background = color

    async def on_click(self, event: events.Click) -> None:
        """
        Handles the click event and sets the highlight color of a specific widget.

        This method is called when the button is clicked. It retrieves
        the widget with the ID "input_prompt" and sets its `highlight_color`
        attribute to the color associated with this button.

        Parameters
        ----------
        event : events.Click
            The click event.
        """
        path_widget = self.app.get_widget_by_id("input_prompt")
        path_widget.highlight_color = self.color


class PathPatternBuilder(DraggableModalScreen):
    """
    A modal screen for interactively building file path patterns.

    This class provides a modal screen that allows users to interactively
    specify file path patterns. It includes color buttons to switch
    between highlight colors, an input field for the path, edit buttons,
    and "Ok" and "Cancel" buttons. The key component is the
    `InputWithColoredSuggestions` widget, which allows for string
    highlighting and pattern suggestions.

    Attributes
    ----------
    title_bar : TitleBar
        The title bar of the modal screen.
    path : str
        The initial file path provided.
    highlight_colors : list[str]
        A list of colors available for highlighting.
    labels : list[str]
        A list of labels used for tagging and identifying segments of the
        path.
    pattern_match_results : dict[str, Any]
        A dictionary that stores the current pattern, feedback message,
        and matched files.
    original_value : str
        The original file path value before user modifications.
    mandatory_tag : str
        A mandatory tag that needs to be present in the path pattern.
    pattern_class : Any
        The class used for creating file pattern steps.

    Methods
    -------
    __init__(path, highlight_colors, labels, title, pattern_class, *args, **kwargs)
        Initializes the PathPatternBuilder.
    on_mount()
        Called when the modal is mounted.
    deactivate_pressed_button()
        Deactivates the currently active button.
    activate_pressed_button(_id)
        Activates the button with the given ID.
    open_browse_window()
        Opens a file browser modal window.
    update_input(selected_path)
        Updates the input prompt with the selected path.
    reset_highlights()
        Resets all highlights in the input prompt.
    reset_all()
        Resets all data and highlights in the input prompt.
    submit_highlights()
        Submits the highlighted path for processing.
    _segment_highlighting_submitted(event)
        Updates pattern_match_results based on the output of various
        methods.
    activate_and_deactivate_press(event)
        Activates and deactivates buttons based on the pressed event.
    _ok(event)
        Confirms the selected pattern and dismisses the modal if valid.
    _ok_part_two()
        Confirms the selected pattern and dismisses the modal if valid.
    _close(event)
        Closes the modal without taking action.
    _remove_self()
        Displays a list of files matching the current pattern.
    on_key(event)
        Handles keyboard input to navigate and toggle highlights.
    key_enter()
        Submits the current path pattern when Enter is pressed.
    key_escape()
        Dismisses the modal when Escape is pressed.
    """

    def __init__(
        self,
        path: str | Text,
        highlight_colors=None,
        labels=None,
        title="X",
        pattern_class=None,
        *args,
        **kwargs,
    ) -> None:
        """
        Initializes the PathPatternBuilder.

        Parameters
        ----------
        path : str | Text
            The initial file path.
        highlight_colors : list[str], optional
            A list of colors available for highlighting, by default None.
        labels : list[str], optional
            A list of labels used for tagging, by default None.
        title : str, optional
            The title of the modal, by default "X".
        pattern_class : Any, optional
            The class used for creating file pattern steps, by default
            None.
        *args : Any
            Additional positional arguments passed to the base class
            constructor.
        **kwargs : Any
            Additional keyword arguments passed to the base class
            constructor.
        """
        super().__init__(*args, **kwargs)
        self.title_bar.title = title
        self.path = path.plain if isinstance(path, Text) else path
        self.highlight_colors = ["red", "green", "blue", "yellow", "magenta"] if highlight_colors is None else highlight_colors
        self.labels = ["subject", "Session", "Run", "Acquisition", "task"] if labels is None else labels
        self.pattern_match_results: dict = {"file_pattern": self.path, "message": "Found 0 files.", "files": []}
        self.original_value = path
        # TODO: since now we are always passing the particular pattern_class to the path_pattern_builder, we do not need
        # to pass colors and labels separately, thus this needs to be cleaned through the whole code
        self.pattern_class = pattern_class
        self.mandatory_tags = [f"{{{label}}}" for label in pattern_class.required_entities]  # f"{{{self.labels[0]}}}"

    def on_mount(self) -> None:
        """
        Called when the modal is mounted.

        This method is called when the modal is mounted. It initializes
        the UI components, including color buttons, the path input field,
        and action buttons.
        """
        colors_and_labels = dict(zip(self.highlight_colors, self.labels, strict=False))
        self.active_button_id = "button_" + self.labels[0]
        color_buttons = [
            ColorButton(label=item[1], color=item[0], id="button_" + item[1], classes="color_buttons")
            for item in colors_and_labels.items()
        ]
        color_buttons[0].add_class("activated")
        self.content.mount(
            Grid(
                *color_buttons,
                id="color_button_panel",
            ),
            HorizontalScroll(
                InputWithColoredSuggestions(
                    [(Text(self.path), self.path)],
                    prompt_default=self.path,
                    colors_and_labels=colors_and_labels,
                    top_parent=self,
                    id="path_widget",
                ),
                id="path_widget_container",
            ),
            Grid(
                Button("Browse", id="browse_button"),
                Button("Reset highlights", id="reset_button"),
                Button("Reset all", id="reset_all"),
                Button("Clear all", id="clear_all"),
                Button("Submit", id="submit_button"),
                id="button_panel",
            ),
            Container(
                Container(
                    Static("Found 0 files.", id="feedback"),
                    Button("👁", id="show_button", classes="icon_buttons"),
                    id="feedback_container",
                ),
                Container(Button("OK", id="ok_button"), Button("Cancel", id="cancel_button"), id="testtt"),
                id="feedback_and_confirm_panel",
            ),
        )
        self.get_widget_by_id("color_button_panel").styles.grid_size_columns = len(self.labels)

    def deactivate_pressed_button(self) -> None:
        """Deactivates the currently active button. Fade the button when inactive."""
        if self.active_button_id is not None:
            self.get_widget_by_id(self.active_button_id).remove_class("activated")

    def activate_pressed_button(self, _id: str) -> None:
        """
        Activates the button with the given ID. Light up the button when inactive.

        Parameters
        ----------
        _id : str
            The ID of the button to activate.
        """
        clicked_color_button = self.get_widget_by_id(_id)
        clicked_color_button.add_class("activated")
        self.active_button_id = _id

    @on(Button.Pressed, "#browse_button")
    def open_browse_window(self) -> None:
        """Opens a file browser modal window."""
        self.app.push_screen(FileBrowserModal(path_test_function=path_test_with_isfile_true), self.update_input)

    def update_input(self, selected_path: str) -> None:
        """
        Updates the input prompt with the selected path.

        Parameters
        ----------
        selected_path : str
            The selected path.
        """
        if selected_path is not None:
            self.get_widget_by_id("input_prompt").value = str(selected_path)
            self.get_widget_by_id("input_prompt").original_value = str(selected_path)

    @on(Button.Pressed, "#reset_button")
    def reset_highlights(self) -> None:
        """Resets all highlights in the input prompt."""
        self.get_widget_by_id("input_prompt").reset_highlights()

    @on(Button.Pressed, "#reset_all")
    def reset_all(self) -> None:
        """Resets all data and highlights in the input prompt."""
        self.get_widget_by_id("input_prompt").reset_all()

    @on(Button.Pressed, "#clear_all")
    def clear_all(self) -> None:
        """Clears the input prompt."""
        self.get_widget_by_id("input_prompt").value = ""

    @on(Button.Pressed, "#submit_button")
    def submit_highlights(self) -> None:
        """Submits the highlighted path for processing."""
        self.get_widget_by_id("input_prompt").submit_path()

    @on(InputWithColoredSuggestions.Changed)
    @on(SegmentHighlighting.Submitted)
    @on(SegmentHighlighting.Changed)
    def _segment_highlighting_submitted(self, event) -> None:
        """
        Updates pattern_match_results based on the output of various methods.

        This method is called when the input value changes or when a
        segment is highlighted and submitted. It updates the
        `pattern_match_results` dictionary with the new file pattern,
        feedback message, and list of files.

        Parameters
        ----------
        event : InputWithColoredSuggestions.Changed | SegmentHighlighting.Submitted | SegmentHighlighting.Changed
            The event object containing information about the change.
        """
        if isinstance(event.value, Text):
            event_value = event.value.plain
            match_feedback_message, filepaths = resolve_path_wildcards(event_value)
            self.path = event_value
        else:
            match_feedback_message, filepaths = resolve_path_wildcards(event.value)
            self.path = event.value

        highlights = self.get_widget_by_id("input_prompt").current_highlights
        self.get_widget_by_id("feedback").update(match_feedback_message)
        self.get_widget_by_id("show_button").tooltip = match_feedback_message
        self.pattern_match_results = {
            "file_pattern": Text(self.path, spans=highlights),
            "message": match_feedback_message,
            "files": filepaths,
        }
        # Change outine from red to green if some files were found.
        if len(self.pattern_match_results["files"]) > 0:
            self.query_one(SelectCurrentWithInputAndSegmentHighlighting).styles.outline = ("solid", "green")
        else:
            self.query_one(SelectCurrentWithInputAndSegmentHighlighting).styles.outline = ("solid", "red")

    @on(Button.Pressed, ".color_buttons")
    def activate_and_deactivate_press(self, event: Button.Pressed) -> None:
        """
        Activates and deactivates buttons based on the pressed event.

        This method is called when a color button is pressed. It
        deactivates the currently active button and activates the pressed
        button.

        Parameters
        ----------
        event : Button.Pressed
            The button pressed event.
        """
        self.deactivate_pressed_button()
        self.activate_pressed_button(event.button.id)

    @on(Button.Pressed, "#ok_button")
    async def _ok(self, event: Button.Pressed) -> None:
        """
        Confirms the selected pattern and dismisses the modal if valid.

        This method is called when the user presses the "Ok" button. It
        validates the selected file pattern and dismisses the modal if
        the pattern is valid. If the pattern is invalid, it displays an
        error message.

        Parameters
        ----------
        event : Button.Pressed
            The button pressed event.
        """
        # Here we try to catch the Marshmallow schema error, if the extension is wrong
        try:
            path = (
                self.pattern_match_results["file_pattern"].plain
                if isinstance(self.pattern_match_results["file_pattern"], Text)
                else self.pattern_match_results["file_pattern"]
            )
            self.pattern_class.check_extension(path)
            self._ok_part_two()
        except Exception as e:
            await self.app.push_screen(
                Confirm(
                    convert_validation_error_to_string(e),
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="File pattern error",
                    classes="confirm_error",
                )
            )

    @work(exclusive=True, name="fill_ctx_spec")
    async def _ok_part_two(self) -> None:
        """
        Confirms the selected pattern and dismisses the modal if valid.

        This method is called after the initial validation in `_ok`. It
        checks if the mandatory tag is present in the file pattern and
        dismisses the modal if the pattern is valid. If the mandatory
        tag is missing, it displays an error message.
        """
        # if all is good from '_ok', continue here
        logger.debug(f"UI->PathPatternBuilder._ok_part_two: mandatory_tags:{self.mandatory_tags}")
        tagglobres = list(tag_glob(self.pattern_match_results["file_pattern"].plain))
        task_set = set()
        for _filepath, tagdict in tagglobres:
            task = tagdict.get("task", None)
            if task is not None:
                task_set.add(task)
        logger.debug(f"UI->PathPatternBuilder._ok_part_two-> ctx.available_images:{ctx.available_images}")
        logger.debug(f"UI->PathPatternBuilder._ok_part_two-> found tasks:{task_set}")

        compatible_task_tags = True
        if ctx.available_images and not task_set < set(ctx.available_images["task"]) and "{task}" in self.mandatory_tags:
            compatible_task_tags = await self.app.push_screen_wait(
                Confirm(
                    f"The task tags are not the same as extracted from the bold files!\n\
The task tags from bold files are:\n{sorted(set(ctx.available_images['task']))}\n\
Your event file task tags are: \n{sorted(task_set)}.\
\nOnly the same tags will be associated together.\nProceed?",
                    left_button_text="YES",
                    right_button_text="NO",
                    left_button_variant="error",
                    right_button_variant="success",
                    title="Task tag mismatch",
                    classes="confirm_warning",
                )
            )

        if not all(tag in self.pattern_match_results["file_pattern"] for tag in self.mandatory_tags):
            # if self.mandatory_tags not in self.pattern_match_results["file_pattern"]:
            self.app.push_screen(
                Confirm(
                    f"Mandatory tag missing! Use all mandatory tags!\n Mandatory tags are: {self.mandatory_tags}!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Missing name",
                    classes="confirm_error",
                )
            )
        elif compatible_task_tags:
            self.dismiss(self.pattern_match_results)

    @on(Button.Pressed, "#cancel_button")
    def _close(self, event: Button.Pressed) -> None:
        """
        Closes the modal without taking action.

        This method is called when the user presses the "Cancel" button. It
        dismisses the modal without taking any action.

        Parameters
        ----------
        event : Button.Pressed
            The button pressed event.
        """
        self.dismiss(False)

    @on(Button.Pressed, "#show_button")
    def _remove_self(self) -> None:
        """
        Displays a list of files matching the current pattern.

        This method is called when the user presses the "Show" button. It
        opens the `ListOfFiles` modal to display the list of files found
        using the current file pattern.
        """
        self.app.push_screen(ListOfFiles(self.pattern_match_results))

    async def on_key(self, event: events.Key) -> None:
        """
        Handles keyboard input to navigate and toggle highlights.

        This method is called when a key is pressed. It handles keyboard
        input to navigate and toggle highlights in the input prompt.

        Parameters
        ----------
        event : events.Key
            The key pressed event.
        """
        path_widget = self.get_widget_by_id("input_prompt")
        if event.key in ["1", "2", "3", "4", "5"]:
            # Set highlight color based on key pressed.
            index = int(event.key) - 1
            path_widget.highlight_color = self.highlight_colors[index]
            self.deactivate_pressed_button()
            self.activate_pressed_button("button_" + self.labels[index])

    def key_enter(self) -> None:
        """
        Submits the current path pattern when Enter is pressed.

        This method is called when the user presses the Enter key. It
        submits the current path pattern for processing.
        """
        self.get_widget_by_id("input_prompt").submit_path()

    def key_escape(self) -> None:
        """
        Dismisses the modal when Escape is pressed.

        This method is called when the user presses the Escape key. It
        dismisses the modal.
        """
        self.dismiss(False)
