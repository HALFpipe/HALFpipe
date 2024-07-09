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
        # self.left_button_text = left_button_text
        # self.right_button_text = right_button_text
        # self.left_button_variant = left_button_variant
        # self.right_button_variant = right_button_variant

        self.title_bar.title = title

        # this here allows to use the modal just with one button, either outputting True or False (left/right)
        # use button_text = False to disable the button
        active_incides = [i for i, val in enumerate([left_button_text, right_button_text]) if val is not False]
        if len(active_incides) == 1:
            active_index = active_incides[0]
            self.buttons = [
                Button(
                    [left_button_text, right_button_text][active_index],
                    variant=[left_button_variant, right_button_variant][active_index],
                    classes=["button ok", "button cancel"][active_index],
                )
            ]
        else:
            self.buttons = [
                Button(left_button_text, variant=left_button_variant, classes="button ok"),
                Button(right_button_text, variant=right_button_variant, classes="button cancel"),
            ]
        print("IIIIIIIIIIINIT Sub Confirm", self.buttons)

    def on_mount(self) -> None:
        self.content.mount(
            # VerticalScroll(
            Static(self.text, id="message"),
            Horizontal(
                *self.buttons,
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
