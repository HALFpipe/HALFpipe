# -*- coding: utf-8 -*-
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from halfpipe.tui.utils.file_browser_modal import FileBrowserModal


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

    def __init__(self, app, path_to, **kwargs) -> None:
        super().__init__(**kwargs)
        self.top_parent = app
        self.path_to = path_to

    def compose(self) -> ComposeResult:
        with Horizontal(id="file_browser"):
            yield Button("Browse", id="file_browser_edit_button", classes="button")
            yield Label(self.path_to + ":", id="path_input_box")

    @on(Button.Pressed, "#file_browser_edit_button")
    def open_browse_window(self):
        self.top_parent.push_screen(FileBrowserModal(), self.update_input)

    @on(Input.Submitted, "#path_input_box")
    def update_from_input(self):
        self.update_input(self.get_widget_by_id("path_input_box").value)

    def update_input(self, selected_path: str) -> None:
        if selected_path != "":
            label = self.get_widget_by_id("path_input_box")
            label.update(self.path_to + ": " + str(selected_path))
            label.value = self.path_to + ": " + str(selected_path)
            self.selected_path = str(selected_path)
