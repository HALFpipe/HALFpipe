# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from halfpipe.tui.utils.file_browser_modal import FileBrowserModal

from ...model.file.bids import BidsFileSchema
from .context import ctx


class FileBrowser(Widget):
    """
    Here goes docstring.
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

    selected_path: reactive[str] = reactive("", init=False)

    @dataclass
    class Changed(Message):
        file_browser: "FileBrowser"
        selected_path: str

        @property
        def control(self):
            return self.file_browser

    def watch_selected_path(self) -> None:
        self.post_message(self.Changed(self, self.selected_path))

    def __init__(self, path_to="", modal_title="Browse", id: str | None = None, classes: str | None = None, **kwargs) -> None:
        super().__init__(id=id, classes=classes)
        #    self.top_parent = app
        self.path_to = path_to
        self.modal_title = modal_title

    def compose(self) -> ComposeResult:
        with Horizontal(id="file_browser"):
            yield Button("Browse", id="file_browser_edit_button", classes="button")
            yield Label(self.path_to + ":", id="path_input_box")

    @on(Button.Pressed, "#file_browser_edit_button")
    def on_button_pressed(self):
        self.open_browse_window()

    def open_browse_window(self):
        print("qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq...0")
        self.app.push_screen(FileBrowserModal(title=self.modal_title), self.update_input)

    @on(Input.Submitted, "#path_input_box")
    def update_from_input(self):
        self.update_input(self.get_widget_by_id("path_input_box").value)

    def update_input(self, selected_path: str) -> None:
        print("uuuuuuuuuuuuuuuuuuuuuuuuuuuuu", selected_path)
        if selected_path != "" and selected_path is not False:
            print("uuuuuuuuuuuuuuuuuuuuuuuuuuuuu 11111111", selected_path)
            label = self.get_widget_by_id("path_input_box")
            label.update(self.path_to + ": " + str(selected_path))
            label.value = self.path_to + ": " + str(selected_path)
            self.selected_path = str(selected_path)


def path_test_for_bids(path, isfile=False):
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
        bold_filedict = {"datatype": "func", "suffix": "bold"}
        ctx.put(BidsFileSchema().load({"datatype": "bids", "path": path}))
        if len(list(ctx.database.get(**bold_filedict))) == 0:
            result_info = "The selected data directory seems not be a BIDS directory! No BOLD files found!"
            ctx.spec.files.pop()
    #
    return result_info


class FileBrowserForBIDS(FileBrowser):
    # def __init__(self, path_to, modal_title="Browse", id: str | None = None, classes: str | None = None, **kwargs) -> None:
    #     super().__init__(path_to=path_to, modal_title=modal_title, id=id, classes=classes)

    def open_browse_window(self):
        print("qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq")
        self.app.push_screen(
            FileBrowserModal(title=self.modal_title, path_test_function=path_test_for_bids), self.update_input
        )
