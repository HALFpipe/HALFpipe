# -*- coding: utf-8 -*-

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Pretty, Static


class ListOfFiles(ModalScreen):
    """Modal for showing the matched files using the given file pattern."""

    def __init__(self, pattern_match_results, **kwargs) -> None:
        super().__init__(**kwargs)
        self.pattern_match_results = pattern_match_results

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(self.pattern_match_results["message"])
            yield ScrollableContainer(Pretty(sorted(self.pattern_match_results["files"])))
            yield Button("Close", id="close_button")

    @on(Button.Pressed, "#close_button")
    def _on_close_button_pressed(self):
        self.app.pop_screen()
