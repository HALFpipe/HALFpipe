# -*- coding: utf-8 -*-
from typing import List

from textual import on
from textual.containers import Container, Horizontal
from textual.widgets import Button, RadioButton, RadioSet, Static

from ..utils.draggable_modal_screen import DraggableModalScreen


class SelectionModal(DraggableModalScreen):
    def __init__(self, options=None, title="", instructions="Select", id: str | None = None, **kwargs) -> None:
        super().__init__(id=id, **kwargs)
        self.title_bar.title = title
        self.instructions = instructions
        RadioButton.BUTTON_INNER = "X"
        self.options = {"a": "A", "b": "B"} if options is None else options
        # self.container_to_mount = Container(
        # Static(self.instructions, id="title"),
        # RadioSet(*[RadioButton(self.options[key]) for key in self.options], id="radio_set"),
        # Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
        # id="top_container",
        # )
        self.choice: str | list = "default_choice??? todo"

    def on_mount(self) -> None:
        """Called when the window is mounted."""
        self.content.mount(
            Static(self.instructions, id="title"),
            RadioSet(*[RadioButton(self.options[key]) for key in self.options], id="radio_set"),
            Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        self.dismiss(self.choice)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)

    # @on(RadioSet.Changed)
    def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.control.id == "radio_set":
            self.choice = list(self.options.keys())[event.index]


class DoubleSelectionModal(SelectionModal):
    def __init__(self, options=None, title="", instructions=None, id: str | None = None, **kwargs) -> None:
        super().__init__(title=title, id=id, **kwargs)
        self.instructions = instructions
        self.options = options
        self.choice: List[str] = ["default_choice??? todo", "1"]
        self.container_to_mount = Container(
            Static(self.instructions[0], id="title_0"),
            RadioSet(*[RadioButton(self.options[0][key]) for key in self.options[0]], id="radio_set_0"),
            Static(self.instructions[1], id="title_1"),
            RadioSet(*[RadioButton(self.options[1][key]) for key in self.options[1]], id="radio_set_1"),
            Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
            id="top_container",
        )

    def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.control.id == "radio_set_0":
            self.choice[0] = list(self.options[0].keys())[event.index]
        if event.control.id == "radio_set_1":
            self.choice[1] = list(self.options[1].keys())[event.index]
