# -*- coding: utf-8 -*-


from dataclasses import dataclass
from typing import Any, Sequence

from inflection import humanize
from rich.text import Text
from textual import on, work
from textual.containers import Horizontal, HorizontalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static
from textual.worker import Worker, WorkerState

from ...ingest.glob import resolve_path_wildcards
from ..data_analyzers.context import ctx
from ..general_widgets.list_of_files_modal import ListOfFiles
from ..specialized_widgets.confirm_screen import SimpleMessageModal
from ..specialized_widgets.path_pattern_builder import PathPatternBuilder  # , resolve_path_wildcards
from .pattern_suggestor import find_tag_positions_by_color, highlighting


class FileItem(Widget):
    """
    Represents a file item widget for selecting file patterns and displaying found files.

    This class provides a widget for selecting file patterns, displaying
    found files, and showing metadata when available. It includes
    functionality for editing the file pattern, showing a list of found
    files, displaying metadata, and deleting the file item. The file pattern
    is provided by the PathPatternBuilder modal and then saved as FilePatternStep
    class instances.

    Attributes
    ----------
    success_value : reactive[bool]
        A reactive attribute indicating whether the file pattern match was
        successful.
    delete_button : bool
        Indicates whether the delete button should be displayed.
    pattern_class : Any | None
        The class used for creating file pattern steps.
    title : str
        The title of the file item.
    load_object : Any | None
        An object containing data to load into the file item.
    callback_message : Text | None
        A message to display in the file item.
    pattern_match_results : dict[str, Any]
        A dictionary containing the results of the pattern match.
    execute_pattern_class_on_mount : bool
        Indicates whether to execute the pattern class on mount.
    from_edit : bool
        Indicates if the widget is opened from edit.

    Methods
    -------
    __init__(
        id,
        classes,
        delete_button,
        title,
        pattern_class,
        id_key,
        load_object,
        callback_message,
        message_dict,
        execute_pattern_class_on_mount,
    )
        Initializes the FileItem widget.
    prettify_message_dict(message_dict) -> Text
        Converts a dictionary of messages into a styled string format.
    callback_func(message_dict)
        Sets the callback message by prettifying the provided message
        dictionary.
    compose() -> ComposeResult
        Composes the UI elements of the FileItem widget.
    on_mount()
        Handles actions upon mounting the widget to the application.
    _on_edit_button_pressed()
        Opens a modal for selecting the search file pattern.
    get_pattern_match_results() -> dict[str, Any]
        Returns the results of the pattern match.
    get_callback_message() -> Text | None
        Returns the callback message.
    get_pattern_class() -> Any | None
        Returns the pattern class.
    _update_file_pattern(pattern_match_results)
        Updates various variables based on the results from the
        PathPatternBuilder modal.
    execute_class()
        Executes additional pattern class actions if applicable.
    on_worker_state_changed(event)
        Handles state changes in the pattern matching worker.
    _on_delete_button_pressed()
        Removes the file pattern item.
    _on_show_button_pressed()
        Shows a modal with the list of files found using the given
        pattern.
    _on_info_button_pressed()
        Shows a modal with meta information from the callback message.
    remove_all_duplicates()
        Removes all duplicate widgets with the same ID.
    update_all_duplicates()
        Updates all duplicate widgets with the same ID.
    """

    # A reactive attribute indicating whether the file pattern match was successful."
    success_value: reactive[bool] = reactive(None, init=False)

    @dataclass
    class IsDeleted(Message):
        """
        A message indicating that a file item has been deleted.

        Attributes
        ----------
        file_item : FileItem
            The file item widget.
        value : str
            The value associated with the deletion (e.g., "yes").
        """

        file_item: "FileItem"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.file_item

    @dataclass
    class SuccessChanged(Message):
        """
        A message indicating that the success state of a file item has changed.

        Attributes
        ----------
        file_item : FileItem
            The file item widget.
        value : str
            The new success value.
        """

        file_item: "FileItem"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.file_item

    @dataclass
    class PathPatternChanged(Message):
        """
        A message indicating that the path pattern of a file item has changed.

        Attributes
        ----------
        file_item : FileItem
            The file item widget.
        value : str
            The new path pattern value.
        """

        file_item: "FileItem"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.file_item

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
        delete_button=True,
        title=None,
        border_title=None,
        pattern_class=None,
        id_key="",
        load_object=None,
        callback_message=None,
        message_dict=None,
        execute_pattern_class_on_mount=True,
    ) -> None:
        """
        Initializes the FileItem widget.

        Parameters
        ----------
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the
            widget, by default None.
        delete_button : bool, optional
            Indicates whether the delete button should be displayed, by
            default True.
        title : str, optional
            The title of the file item, by default "".
        pattern_class : Any, optional
            The class used for creating file pattern steps, by default
            None.
        id_key : str, optional
            An identifier key, by default "".
        load_object : Any, optional
            An object containing data to load into the file item, by
            default None.
        callback_message : Text, optional
            A message to display in the file item, by default None.
        message_dict : dict, optional
            A dictionary of messages to display in the file item, by
            default None.
        execute_pattern_class_on_mount : bool, optional
            Indicates whether to execute the pattern class on mount, by
            default True.
        """
        super().__init__(id=id, classes=classes)
        # Indicates whether the delete button should be displayed.
        self.delete_button = delete_button
        # The class used for creating file pattern steps.
        self.pattern_class = None if pattern_class is None else pattern_class
        # The title of the file item.
        self.title = "" if title is None else title
        if self.pattern_class is not None and self.title == "":
            self.title = self.pattern_class.header_str
            if self.pattern_class.next_step_type is not None:
                self.pattern_class.callback = self.callback_func
            self.pattern_class.id_key = id

        # An object containing data to load into the file item.
        self.load_object = load_object
        self.border_title = None if border_title is None else border_title
        # Indicates if the widget is opened from edit.
        self.from_edit = False
        # A message to display in the file item.
        if message_dict is not None and callback_message is None:
            self.callback_message = self.prettify_message_dict(message_dict)
        else:
            self.callback_message = callback_message

        self.pattern_match_results: dict = {"file_pattern": "", "message": "Found 0 files.", "files": [], "file_tag": None}
        self.execute_pattern_class_on_mount = execute_pattern_class_on_mount

    def prettify_message_dict(self, message_dict: dict[str, list[str]]) -> Text:
        """
        Converts a dictionary of messages into a styled string format.

        This method takes a dictionary of messages, formats them into a
        rich text string, and returns the result.

        Parameters
        ----------
        message_dict : dict[str, list[str]]
            A dictionary where keys are message categories and values are
            lists of messages.

        Returns
        -------
        Text
            A rich text string containing the formatted messages.
        """
        info_string = Text("")
        for key in message_dict:
            # if there is only one item, we do not separate items on new lines
            if len(message_dict[key]) <= 1:
                sep_char = ""
                separ_line = "-" * (len(key) + len(message_dict[key]) + 3)
            else:
                sep_char = "\n"
                separ_line = "-" * (max([len(s) for s in [key] + message_dict[key]]) + 3)
            message_value = ""
            for message in message_dict[key]:
                message_value += message + " " if message.endswith("\n") else message + "\n"
            info_string += (
                Text(humanize(key) + ": " + sep_char, style="bold green")
                + Text(message_value + separ_line, style="white")
                + "\n"
            )
        return info_string

    def callback_func(self, message_dict):
        """
        Sets the callback message by prettifying the provided message dictionary.

        This method takes a dictionary of messages, formats them into a
        rich text string using `prettify_message_dict`, and stores the
        result in the `callback_message` attribute.

        Parameters
        ----------
        message_dict : dict[str, list[str]]
            A dictionary where keys are message categories and values are
            lists of messages.
        """
        self.callback_message = self.prettify_message_dict(message_dict)

    def compose(self):
        """
        Composes the UI elements of the FileItem widget.

        This method defines the layout and components of the widget,
        including a static label for the file pattern, and buttons for
        info, edit, show, and delete (optional).
        """
        yield HorizontalScroll(Static("Edit to enter the file pattern", id="static_file_pattern"))
        with Horizontal(id="icon_buttons_container"):
            yield Button(" ℹ", id="info_button", classes="icon_buttons")

            yield Button("🖌", id="edit_button", classes="icon_buttons")
            yield Button("👁", id="show_button", classes="icon_buttons")
            if self.delete_button:
                yield Button("❌", id="delete_button", classes="icon_buttons")

    def on_mount(self) -> None:
        """
        Handles actions upon mounting the widget to the application.

        This method is called when the widget is mounted to the
        application. It sets up tooltips for the buttons and, if
        `load_object` is None, it opens the `PathPatternBuilder` modal to
        allow the user to define the file pattern. If `load_object` is
        not None, it loads the file pattern from the provided object (
        this is used when for example we load from a spec file).
        """
        if self.load_object is None:
            self.get_widget_by_id("edit_button").tooltip = "Edit"
            if self.delete_button:
                self.get_widget_by_id("delete_button").tooltip = "Delete"
            if self.pattern_class is not None:
                self.app.push_screen(
                    PathPatternBuilder(
                        path="/",
                        title=self.title,
                        highlight_colors=self.pattern_class.get_entity_colors_list,
                        labels=self.pattern_class.get_entities,
                        pattern_class=self.pattern_class,
                    ),
                    self._update_file_pattern,
                )
        else:
            if isinstance(self.load_object, dict):
                self._update_file_pattern(self.load_object)
            else:
                pattern_load = {}
                pattern_load["file_pattern"] = self.load_object.path
                if self.load_object.tags == {}:
                    pattern_load["file_tag"] = None
                else:
                    pattern_load["file_tag"] = self.load_object.tags.get("desc", self.load_object.tags.get("atlas"))

                message, filepaths = resolve_path_wildcards(self.load_object.path)
                pattern_load["message"] = message
                pattern_load["files"] = filepaths
                self._update_file_pattern(pattern_load)
        if (self.pattern_class and self.pattern_class.callback) or self.callback_message:
            self.get_widget_by_id("info_button").styles.visibility = "visible"
        else:
            self.get_widget_by_id("info_button").remove()

    @on(Button.Pressed, "#edit_button")
    def _on_edit_button_pressed(self, event):
        """
        Opens a modal for selecting the search file pattern.

        This method is called when the user presses the "Edit" button. It
        opens the `PathPatternBuilder` modal to allow the user to edit
        the file pattern.
        """
        if "-read-only" not in event.control.classes:
            self.from_edit = True
            if self.pattern_class is not None:
                self.app.push_screen(
                    PathPatternBuilder(
                        path=self.pattern_match_results["file_pattern"],
                        title=self.title,
                        highlight_colors=self.pattern_class.get_entity_colors_list,
                        labels=self.pattern_class.get_entities,
                        pattern_class=self.pattern_class,
                    ),
                    self._update_file_pattern,
                )

    @property
    def get_pattern_match_results(self) -> dict[str, Any]:
        """
        Returns the results of the pattern match.

        Returns
        -------
        dict[str, Any]
            A dictionary containing the results of the pattern match.
        """
        return self.pattern_match_results

    @property
    def get_callback_message(self) -> Sequence[str] | None:
        """
        Returns the callback message.

        Returns
        -------
        Sequence[str] | None
            The callback message, or None if no message is set.
        """
        return self.callback_message

    @property
    def get_pattern_class(self):
        return self.pattern_class

    # runs after the PathPatternBuilder modal
    @work(exclusive=True, name="update_worker")
    async def _update_file_pattern(self, pattern_match_results):
        """
        Updates various variables based on the results from the PathPatternBuilder modal.

        This method is called after the `PathPatternBuilder` modal is
        closed. It updates the file pattern, message, and file list based
        on the results from the modal. It also updates the UI to reflect
        the new file pattern and the number of files found.

        Parameters
        ----------
        pattern_match_results : dict | bool
            The results from the `PathPatternBuilder` modal, or False if
            the modal was canceled.
        """
        if pattern_match_results is not False:
            self.pattern_match_results = pattern_match_results
            # Update the static label using the file pattern.

            if self.pattern_class is not None:
                colors_and_labels = dict(
                    zip(self.pattern_class.get_entity_colors_list, self.pattern_class.get_entities, strict=False)
                )
                current_highlights = find_tag_positions_by_color(pattern_match_results["file_pattern"], colors_and_labels)
            else:
                current_highlights = []

            # ensure that this is a string before wrapping it as rich Text
            pattern_match_results["file_pattern"] = (
                pattern_match_results["file_pattern"].plain
                if isinstance(pattern_match_results["file_pattern"], Text)
                else pattern_match_results["file_pattern"]
            )
            self.get_widget_by_id("static_file_pattern").update(
                highlighting(Text(pattern_match_results["file_pattern"]), current_highlights)
            )
            # Tooltip telling us how many files were  found.
            self.get_widget_by_id("show_button").tooltip = pattern_match_results["message"]
            # If 0 files were found, the border is red, otherwise green.
            if len(pattern_match_results["files"]) > 0:
                self.styles.border = ("solid", "green")
                self.success_value = True
                if pattern_match_results["file_tag"] is not None:
                    self.border_title = f"File tag: {pattern_match_results['file_tag']}"
            else:
                self.styles.border = ("solid", "red")
                self.success_value = False
            if len(pattern_match_results["files"]) > 0:
                if self.pattern_class is not None and self.execute_pattern_class_on_mount:
                    await self.execute_class()

            if self.from_edit:
                # await self.update_all_duplicates()
                pass

        else:
            # delete it self if cancelled and was not existing before
            if self.pattern_match_results["file_pattern"] == "":
                self.remove_all_duplicates()
                self.remove()

    async def execute_class(self) -> None:
        """
        Executes additional pattern class actions if applicable.

        This method executes additional actions defined in the pattern
        class, such as pushing the file path to the context object.
        """
        if self.pattern_class is not None:
            # fix this because sometimes this can be just ordinary string
            file_pattern = self.pattern_match_results["file_pattern"]
            if isinstance(file_pattern, Text):
                file_pattern = file_pattern.plain

            await self.pattern_class.push_path_to_context_obj(
                path=file_pattern,
                tags=self.pattern_match_results["file_tag"],
            )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """
        Handles state changes in the pattern matching worker.

        This method is called when the state of the `update_worker`
        changes. If the worker is successful, it updates the
        `pattern_match_results` with the callback message and posts a
        `PathPatternChanged` message.

        Parameters
        ----------
        event : Worker.StateChanged
            The event object containing information about the worker state
            change.
        """
        if event.worker.name == "update_worker":
            if event.state == WorkerState.SUCCESS:
                callback_message = self.get_callback_message
                self.pattern_match_results["callback_message"] = callback_message if callback_message is not None else []
                self.post_message(self.PathPatternChanged(self, self.pattern_match_results))

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self, event) -> None:
        """
        Removes the file pattern item.

        This method is called when the user presses the "Delete" button.
        It removes the file item from the cache (if it exists) and posts
        an `IsDeleted` message.
        """
        # Creation of the FileItem does not automatically imply creation in the cache.
        # For this a pattern needs to be created. By cancelling the modal, the widget is created but the filepattern is not.
        if "-read-only" not in event.control.classes:
            if self.id in ctx.cache:
                ctx.cache.pop(self.id)
                self.remove_all_duplicates()
            self.post_message(self.IsDeleted(self, self.pattern_match_results))


    @on(Button.Pressed, "#show_button")
    def _on_show_button_pressed(self) -> None:
        """
        Shows a modal with the list of files found using the given pattern.

        This method is called when the user presses the "Show" button. It
        opens the `ListOfFiles` modal to display the list of files found
        using the current file pattern.
        """
        self.app.push_screen(ListOfFiles(self.pattern_match_results))

    @on(Button.Pressed, "#info_button")
    def _on_info_button_pressed(self) -> None:
        """
        Shows a modal with meta information from the callback message.

        This method is called when the user presses the "Info" button. It
        opens the `SimpleMessageModal` to display the meta information
        from the callback message.
        """
        self.app.push_screen(SimpleMessageModal(self.callback_message, title="Meta information"))

    def remove_all_duplicates(self) -> None:
        """
        Removes all duplicate widgets with the same ID.

        This method removes all other `FileItem` widgets with the same ID
        as the current widget.
        """
        for w in self.app.walk_children(FileItem):
            # remove itself standardly later
            if w.id == self.id and w != self:
                w.remove()

    async def update_all_duplicates(self) -> None:
        """
        Updates all duplicate widgets with the same ID.

        This method updates all other `FileItem` widgets with the same ID
        as the current widget to have the same pattern match results.
        """
        for w in self.app.walk_children(FileItem):
            # remove itself standardly later
            if w.id == self.id and w != self:
                if w.pattern_match_results != self.pattern_match_results:
                    await w._update_file_pattern(self.pattern_match_results)
        self.from_edit = False
