# -*- coding: utf-8 -*-
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class FalseInputWarning(ModalScreen):
    CSS_PATH = ["tcss/false_input_warning.tcss"]

    def __init__(self, warning_message) -> None:
        self.warning_message = warning_message
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.warning_message),
            Horizontal(Button("Ok", variant="warning")),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    def key_escape(self):
        self.app.pop_screen()
