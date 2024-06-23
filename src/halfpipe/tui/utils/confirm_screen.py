# -*- coding: utf-8 -*-
from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, Static

from .draggable_modal_screen import DraggableModalScreen


class Confirm(DraggableModalScreen):
    CSS_PATH = ["tcss/confirm.tcss"]

    def __init__(
        self,
        text="Are you sure?",
        left_button_text="Ok",
        right_button_text="Cancel",
        left_button_variant="success",
        right_button_variant="error",
        title="",
        id: str | None = None,
        classes: str | None = None,
        width=None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.text = text
        self.left_button_text = left_button_text
        self.right_button_text = right_button_text
        self.left_button_variant = left_button_variant
        self.right_button_variant = right_button_variant

        self.title_bar.title = title
        print("IIIIIIIIIIINIT Sub Confirm")

    # def compose(self) -> ComposeResult:
    # yield Container(
    # Container(Label(self.text, id="message"), classes="message_container"),
    # Grid(
    # Button(self.left_button_text, variant="success", classes="button ok"),
    # Button(self.right_button_text, variant="error", classes="button cancel"),
    # classes="button_grid",
    # ),
    # id="confirm_screen",
    # )

    def on_mount(self) -> None:
        self.content.mount(
            # VerticalScroll(
            Static(self.text, id="message"),
            Horizontal(
                Button(self.left_button_text, variant=self.left_button_variant, classes="button ok"),
                Button(self.right_button_text, variant=self.right_button_variant, classes="button cancel"),
                classes="button_grid",
            ),
            #    id="confirm_screen",
            # )
        )
        # self.content.add_class('
        print("OOOOOOOOOOOOOOONmount Sub Confirm")

    @on(Button.Pressed, ".button_grid .ok")
    def ok(self):
        self._confirm_window()

    @on(Button.Pressed, ".button_grid .cancel")
    def cancel(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        self.dismiss(True)

    def _cancel_window(self):
        self.dismiss(False)
