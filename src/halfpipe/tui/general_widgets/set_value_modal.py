# -*- coding: utf-8 -*-


from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from ..general_widgets.draggable_modal_screen import DraggableModalScreen
from ..help_functions import is_number_string
from ..specialized_widgets.confirm_screen import Confirm


class SetValueModal(DraggableModalScreen):
    """
    A modal dialog for setting a value via user input.

    This class provides a modal screen that allows the user to input a
    value. It includes instructions, an input field, and action buttons
    (typically "Ok" and "Cancel").

    Parameters
    ----------
    instructions : str, optional
        Instructions to be displayed at the top of the modal,
        by default "Set value".
    left_button_text : str, optional
        Text for the left button (typically "Ok"), by default "Ok".
    right_button_text : str, optional
        Text for the right button (typically "Cancel"), by default "Cancel".
    left_button_variant : str, optional
        Variant type for the left button (e.g., "success"),
        by default "success".
    right_button_variant : str, optional
        Variant type for the right button (e.g., "error"),
        by default "error".
    title : str, optional
        Title for the modal, by default "".
    id : str | None, optional
        An optional ID for the modal, by default None.
    classes : str | None, optional
        An optional string of classes for the modal, by default None.

    Attributes
    ----------
    CSS_PATH : list[str]
        List of CSS files to be used for styling.
    instructions : str
        The instruction text displayed in the modal.
    left_button_text : str
        The text displayed on the left button.
    right_button_text : str
        The text displayed on the right button.
    left_button_variant : str
        The variant type of the left button.
    right_button_variant : str
        The variant type of the right button.

    Methods
    -------
    on_mount()
        Mounts the content of the modal, including instructions, input
        field, and action buttons.
    _on_ok_button_pressed()
        Handles the event when the OK button is pressed.
    _on_cancel_button_pressed()
        Handles the event when the Cancel button is pressed.
    """

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
        """
        Initializes the SetValueModal.

        Parameters
        ----------
        instructions : str, optional
            Instructions to be displayed at the top of the modal,
            by default "Set value".
        left_button_text : str, optional
            Text for the left button (typically "Ok"), by default "Ok".
        right_button_text : str, optional
            Text for the right button (typically "Cancel"),
            by default "Cancel".
        left_button_variant : str, optional
            Variant type for the left button (e.g., "success"),
            by default "success".
        right_button_variant : str, optional
            Variant type for the right button (e.g., "error"),
            by default "error".
        title : str, optional
            Title for the modal, by default "".
        id : str | None, optional
            An optional ID for the modal, by default None.
        classes : str | None, optional
            An optional string of classes for the modal, by default None.
        """
        super().__init__(id=id, classes=classes)
        # The instruction text displayed in the modal.
        self.instructions: str = instructions
        # The text displayed on the left button.
        self.left_button_text: str | bool = left_button_text
        # The text displayed on the right button.
        self.right_button_text: str | bool = right_button_text
        # The variant type of the left button.
        self.left_button_variant: str = left_button_variant
        # The variant type of the right button.
        self.right_button_variant: str = right_button_variant
        self.title_bar.title = title

        active_incides = [i for i, val in enumerate([left_button_text, right_button_text]) if val is not False]
        # The index of the active button when only one button is displayed.
        self.active_index = None
        if len(active_incides) == 1:
            active_index = active_incides[0]
            self.active_index = active_index
            self.buttons = [
                Button(
                    [left_button_text, right_button_text][active_index],
                    variant=[left_button_variant, right_button_variant][active_index],
                    classes=["button ok", "button cancel"][active_index],
                    id="only_one_button",
                )
            ]
        else:
            self.buttons = [
                Button(left_button_text, variant=left_button_variant, classes="button ok", id="ok_left_button"),
                Button(right_button_text, variant=right_button_variant, classes="button cancel", id="cancel_right_button"),
            ]

    def on_mount(self) -> None:
        self.content.mount(
            Static(self.instructions), Input("0", id="input_prompt"), Horizontal(*self.buttons, classes="button_grid")
        )

    @on(Button.Pressed, ".ok")
    def _on_ok_button_pressed(self):
        input_widget = self.query_one(Input)
        if input_widget.value == "" or not is_number_string(input_widget.value):
            self.app.push_screen(
                Confirm(
                    "Enter a numerical value!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Value error",
                    classes="confirm_error",
                )
            )
        else:
            self.dismiss(input_widget.value)

    @on(Button.Pressed, ".cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)
