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
    A modal screen for inputting a name.

    This class provides a modal screen that allows users to input a name.
    It includes an input field for the name, "Ok" and "Cancel" buttons,
    and validation to ensure the name is not empty and does not already
    exist.

    Attributes
    ----------
    occupied_feature_names : list[str]
        A list of names that are already in use.
    default_value : str | None
        An optional default value to pre-fill the input field.

    Methods
    -------
    __init__(occupied_feature_names)
        Initializes the NameInput modal.
    on_mount()
        Called when the modal is mounted.
    _ok()
        Handles the "Ok" button press event.
    _cancel()
        Handles the "Cancel" button press event.
    key_escape()
        Handles the Escape key press event.
    _confirm_window()
        Confirms the input name and performs validation checks.
    _cancel_window()
        Closes the modal without confirmation.
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

    def __init__(self, occupied_feature_names, default_value=None) -> None:
        """
        Initializes the NameInput modal.

        Parameters
        ----------
        occupied_feature_names : list[str]
            A list of names that are already in use.
        default_value : str | None, optional
            An optional default value to pre-fill the input field, by default None.
        """
        self.occupied_feature_names = occupied_feature_names
        super().__init__()
        self.title_bar.title = "Feature name"
        self.default_value = default_value if default_value is not None else None

    def on_mount(self) -> None:
        """
        Called when the modal is mounted.

        This method is called when the modal is mounted. It initializes
        the UI components, including the input field and the "Ok" and
        "Cancel" buttons.
        """
        self.content.mount(
            Input(
                value=self.default_value,
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
    def ok(self) -> None:
        """
        Called when the modal is mounted.

        This method is called when the modal is mounted. It initializes
        the UI components, including the input field and the "Ok" and
        "Cancel" buttons.
        """
        self._confirm_window()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        """
        Handles the "Cancel" button press event.

        This method is called when the user presses the "Cancel" button.
        It calls `_cancel_window` to close the modal without confirmation.
        """
        self._cancel_window()

    def key_escape(self) -> None:
        """
        Handles the Escape key press event.

        This method is called when the user presses the Escape key. It
        calls `_cancel_window` to close the modal without confirmation.
        """
        self._cancel_window()

    def _confirm_window(self):
        """
        Confirms the input name and performs validation checks.

        This method is called to confirm the input name. It checks if the
        name is empty or if it already exists in
        `occupied_feature_names`. If the name is invalid, it displays an
        error message. Otherwise, it dismisses the modal with the input
        name.
        """
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
        """
        Closes the modal without confirmation.

        This method is called to close the modal without confirming the
        input name. It dismisses the modal with a value of None.
        """
        self.dismiss(None)
