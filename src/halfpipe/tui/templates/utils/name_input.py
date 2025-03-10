# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-


from textual import on
from textual.containers import Horizontal
from textual.widgets import (
    Button,
    Input,
)

from ...general_widgets.draggable_modal_screen import DraggableModalScreen
from ...specialized_widgets.confirm_screen import Confirm


class NameInput(DraggableModalScreen):
    """
    NameInput Class for a Draggable Modal Screen input interface.

    Attributes
    ----------
    CSS_PATH : list
        The CSS paths used by the class.

    Methods
    -------
    __init__(occupied_feature_names)
        Initializes the NameInput class with occupied feature names.

    on_mount()
        Mounts the input field and buttons on the modal screen when it is created.

    ok()
        Handles the 'Ok' button press event.

    cancel()
        Handles the 'Cancel' button press event.

    key_escape()
        Handles escape key press to cancel the modal.

    _confirm_window()
        Confirms the input feature name and performs validation checks.

    _cancel_window()
        Closes the modal window without confirmation.
    """

    DEFAULT_CSS = """
    NameInput {
        align: center middle;
        width: 60;
        height: 9;
        .feature_name {
            height: 3;
            width: 40;
            margin: 2;
        }
        .button_grid {
            width: 100%;
            height: auto;

            align: right middle;
        }
        .button {
            margin: 0 1 0 0;
        }
    }
    """

    def __init__(self, occupied_feature_names) -> None:
        self.occupied_feature_names = occupied_feature_names
        super().__init__()
        self.title_bar.title = "Feature name"

    def on_mount(self) -> None:
        self.content.mount(
            Input(
                placeholder="Enter feature name",
                id="feature_name",
                classes="feature_name",
            ),
            Horizontal(
                Button("Ok", id="ok", classes="button"),
                Button("Cancel", id="cancel", classes="button"),
                classes="button_grid",
            ),
        )

    @on(Button.Pressed, "#ok")
    def ok(self):
        self._confirm_window()

    @on(Button.Pressed, "#cancel")
    def cancel(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        feature_name = self.get_widget_by_id("feature_name").value
        if feature_name == "":
            self.app.push_screen(
                Confirm(
                    "Enter a name!",
                    left_button_text=False,
                    right_button_text="OK",
                    #  left_button_variant=None,
                    right_button_variant="default",
                    title="Missing name",
                    classes="confirm_error",
                )
            )

        elif feature_name in self.occupied_feature_names:
            self.app.push_screen(
                Confirm(
                    "Name already exists!\nUse another one.",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Existing name",
                    classes="confirm_error",
                )
            )
        else:
            self.dismiss(feature_name)

    def _cancel_window(self):
        self.dismiss(None)
