# -*- coding: utf-8 -*-

from textual import on
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Button, Static

from .draggable_modal_screen import DraggableModalScreen


class ListOfFiles(DraggableModalScreen):
    """Modal for showing the matched files using the given file pattern."""

    def __init__(self, pattern_match_results, **kwargs) -> None:
        super().__init__(**kwargs)
        self.pattern_match_results = pattern_match_results
        self.title_bar.title = "List of matching files"

    def on_mount(self) -> None:
        self.content.mount(
            Static(self.pattern_match_results["message"], id="message"),
            # ScrollableContainer(Static('\n'.join(self.pattern_match_results["files"])))),
            ScrollableContainer(Static("\n".join(sorted(self.pattern_match_results["files"])), id="file_list")),
            Horizontal(Button("Close", id="close_button"), id="close_button_container"),
        )

    @on(Button.Pressed, "#close_button")
    def _on_close_button_pressed(self):
        self.app.pop_screen()
