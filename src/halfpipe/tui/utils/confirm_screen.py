# -*- coding: utf-8 -*-
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class Confirm(ModalScreen):
    CSS_PATH = ["tcss/confirm.tcss"]

    def __init__(self, text="Are you sure?", left_button_text="Ok", right_button_text="Cancel") -> None:
        super().__init__()
        self.text = text
        self.left_button_text = left_button_text
        self.right_button_text = right_button_text

    def compose(self) -> ComposeResult:
        yield Container(
            Container(Label(self.text, id="message"), classes="message_container"),
            Grid(
                Button(self.left_button_text, variant="success", classes="button ok"),
                Button(self.right_button_text, variant="error", classes="button cancel"),
                classes="button_grid",
            ),
            id="confirm_screen",
        )

    @on(Button.Pressed, "#confirm_screen .ok")
    def ok(self):
        self._confirm_window()

    @on(Button.Pressed, "#confirm_screen .cancel")
    def cancel(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        self.dismiss(True)

    def _cancel_window(self):
        self.dismiss(False)
