# -*- coding: utf-8 -*-
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label

from .draggable_modal_screen import DraggableModalScreen


class FalseInputWarning(DraggableModalScreen):
    CSS_PATH = ["tcss/false_input_warning.tcss"]

    def __init__(
        self, warning_message, title="", id: str | None = None, classes: str | None = None, button_variant="error"
    ) -> None:
        self.warning_message = warning_message
        super().__init__(id=id, classes=classes)
        self.title_bar.title = title
        self.button_variant = button_variant

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Label(self.warning_message),
                Horizontal(Button("Ok", variant=self.button_variant)),
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def key_escape(self):
        self.dismiss()


class SimpleMessageModal(FalseInputWarning):
    def __init__(self, warning_message, title="", id: str | None = None, classes: str | None = None) -> None:
        super().__init__(warning_message, title=title, id=id, classes=classes, button_variant="default")
