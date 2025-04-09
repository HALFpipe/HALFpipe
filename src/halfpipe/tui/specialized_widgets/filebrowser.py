# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass

from bids import BIDSLayout
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from .file_browser_modal import FileBrowserModal


class FileBrowser(Widget):
    """
    A widget for browsing and selecting files or directories.

    This class provides a user interface for browsing and selecting files
    or directories. It includes a button to open a file browser modal and
    a label to display the selected path.

    Attributes
    ----------
    DEFAULT_CSS : str
        The default CSS styling for the FileBrowser widget.
    selected_path : reactive[str]
        A reactive attribute that stores the currently selected path.

    Methods
    -------
    watch_selected_path()
        Posts a message when the selected_path attribute changes.
    __init__(path_to, modal_title, id, classes, **kwargs)
        Initializes the FileBrowser widget.
    compose() -> ComposeResult
        Composes the widget's components.
    on_button_pressed()
        Handles the event when the browse button is pressed.
    open_browse_window()
        Opens the file browsing modal window.
    update_from_input()
        Updates the selected path based on user input.
    update_input(selected_path)
        Updates the UI with the selected path.
    """

    DEFAULT_CSS = """
    FileBrowser {
        border: tall transparent;
        background: $boost;
        height: auto;
        width: auto;
        padding: 0 2;
    }
    """

    # A reactive attribute that stores the currently selected path.
    # selected_path: reactive[str] = reactive("", init=False)

    @dataclass
    class Changed(Message):
        file_browser: "FileBrowser"
        selected_path: str

        @property
        def control(self):
            return self.file_browser

    # def watch_selected_path(self) -> None:
    #     self.post_message(self.Changed(self, self.selected_path))

    def __init__(self, path_to="", modal_title="Browse", id: str | None = None, classes: str | None = None, **kwargs) -> None:
        """
        Initializes the FileBrowser widget.

        Parameters
        ----------
        path_to : str, optional
            A descriptive label for the path, by default "".
        modal_title : str, optional
            The title of the file browser modal, by default "Browse".
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the
            widget, by default None.
        **kwargs : dict
            Additional keyword arguments.
        """
        super().__init__(id=id, classes=classes)
        # A descriptive label for the path.
        self.path_to = path_to
        # The title of the file browser modal.
        self.modal_title = modal_title

    def compose(self) -> ComposeResult:
        """
        Composes the widget's components.

        This method defines the layout and components of the widget,
        including a "Browse" button and a label to display the selected
        path.

        Yields
        ------
        ComposeResult
            The composed widgets.
        """
        with Horizontal(id="file_browser"):
            yield Button("Browse", id="file_browser_edit_button", classes="button")
            yield Label(self.path_to + ":", id="path_input_box")

    @on(Button.Pressed, "#file_browser_edit_button")
    def on_button_pressed(self) -> None:
        """
        Handles the event when the browse button is pressed.

        This method is called when the user presses the "Browse" button.
        It calls `open_browse_window` to open the file browser modal.
        """
        self.open_browse_window()

    def open_browse_window(self) -> None:
        """
        Opens the file browsing modal window.

        This method pushes the `FileBrowserModal` onto the screen to allow
        the user to browse and select a file or directory.
        """
        self.app.push_screen(FileBrowserModal(title=self.modal_title), self.update_input)

    @on(Input.Submitted, "#path_input_box")
    def update_from_input(self) -> None:
        """
        Updates the selected path based on user input.

        This method is called when the user submits a value in the path
        input box. It calls `update_input` to update the UI with the new
        path.
        """
        self.update_input(self.get_widget_by_id("path_input_box").value)
        self.post_message(self.Changed(self, self.selected_path))

    def update_input(self, selected_path: str, send_message: bool = True) -> None:
        """
        Updates the UI with the selected path.

        This method is called when a new path is selected. It updates the
        label to display the selected path and updates the
        `selected_path` attribute.

        Parameters
        ----------
        selected_path : str
            The newly selected path.
        """
        if selected_path != "" and selected_path is not False:
            label = self.get_widget_by_id("path_input_box")
            label.update(self.path_to + ": " + str(selected_path))
            label.value = self.path_to + ": " + str(selected_path)
            self.selected_path = str(selected_path)
            if send_message:
                self.post_message(self.Changed(self, self.selected_path))


def path_test_for_bids(path: str, isfile: bool = False) -> str:
    """
    Checks if a given directory is a valid BIDS dataset.

    This function checks if a given path is a valid BIDS dataset. It
    also checks if the path exists, is writable, and is a directory.

    Parameters
    ----------
    path : str
        The path to the directory to be checked.
    isfile : bool, optional
        This parameter is not used in this function, by default False.

    Returns
    -------
    str
        A message indicating the result of the path check. Possible
        values are:
        - "OK" if the path is a valid BIDS dataset and is writable.
        - "Permission denied." if the path is not writable.
        - "File not found." if the path does not exist.
        - An error message if the path is not a valid BIDS dataset.
    """
    if os.path.exists(path):
        if os.access(path, os.W_OK):
            if isfile:
                result_info = "OK" if os.path.isfile(path) else "A directory was selected instead of a file!"
            else:
                result_info = "OK" if os.path.isdir(path) else "A file was selected instead of a directory!"
        else:
            result_info = "Permission denied."
    else:
        result_info = "File not found."
    if result_info == "OK":
        """
        Checks if a given directory is a valid BIDS dataset.
        """

        try:
            BIDSLayout(path, validate=True)  # Enforce validation
        except Exception as e:
            print(f"Invalid BIDS dataset: {e}")
            result_info = f"The selected data directory seems not be a BIDS directory!\nException: {e}"
    return result_info


class FileBrowserForBIDS(FileBrowser):
    """
    A specialized file browser for selecting BIDS-compatible directories.

    This class extends `FileBrowser` to provide a file browser that
    specifically checks for BIDS-compatible directories.

    Methods
    -------
    open_browse_window()
        Opens a file browsing window with a BIDS-specific path test.
    """

    def open_browse_window(self):
        """
        Opens a file browsing window with a BIDS-specific path test.

        This method overrides the `open_browse_window` method of the
        parent class to use the `path_test_for_bids` function for
        validating the selected path.
        """
        self.app.push_screen(
            FileBrowserModal(title=self.modal_title, path_test_function=path_test_for_bids), self.update_input
        )
