# -*- coding: utf-8 -*-


from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from ..utils.draggable_modal_screen import DraggableModalScreen


class SetValueModal(DraggableModalScreen):
    CSS_PATH = ["tcss/set_value_modal.tcss"]

    def __init__(
        self,
        instructions="Set value",
        left_button_text="Ok",
        right_button_text="Cancel",
        left_button_variant="success",
        right_button_variant="error",
        title="",
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.instructions = instructions
        self.left_button_text = left_button_text
        self.right_button_text = right_button_text
        self.left_button_variant = left_button_variant
        self.right_button_variant = right_button_variant

        self.title_bar.title = title

    def on_mount(self) -> None:
        self.content.mount(
            Static(self.instructions),
            Input(""),
            Horizontal(
                Button(self.left_button_text, variant=self.left_button_variant, classes="button ok"),
                Button(self.right_button_text, variant=self.right_button_variant, classes="button cancel"),
                classes="button_grid",
            ),
        )

    @on(Button.Pressed, ".ok")
    def _on_ok_button_pressed(self):
        input_widget = self.query_one(Input)
        if input_widget.value == "":
            self.dismiss("0")
        else:
            self.dismiss(input_widget.value)

    @on(Button.Pressed, ".cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)
