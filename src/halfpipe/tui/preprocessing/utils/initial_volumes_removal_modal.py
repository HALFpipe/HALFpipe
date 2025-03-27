from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from ...general_widgets.draggable_modal_screen import DraggableModalScreen


class SetInitialVolumesRemovalModal(DraggableModalScreen):
    """
    A modal dialog for setting the number of initial volumes to remove.

    This modal allows users to specify the number of initial volumes to
    remove from functional scans. It includes an input field for the
    number of volumes and "OK" and "Cancel" buttons.

    Methods
    -------
    __init__(**kwargs)
        Initializes the modal with a title.
    on_mount()
        Sets up the modal content including a prompt, input field, and
        OK/Cancel buttons.
    _on_ok_button_pressed()
        Handles the OK button press event, retrieves the input value, and
        dismisses the modal with the given input.
    _on_cancel_button_pressed()
        Handles the Cancel button press event and dismisses the modal with
        False.
    """

    def __init__(self, **kwargs):
        """
        Initializes the SetInitialVolumesRemovalModal.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments passed to the base class constructor.
        """
        super().__init__(**kwargs)
        self.title_bar.title = "Remove initial volumes"

    def on_mount(self) -> None:
        self.content.mount(
            Static("Set number of how many initial volumes to remove"),
            Input("", id="input_prompt"),
            Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        input_widget = self.query_one(Input)
        if input_widget.value == "":
            self.dismiss("0")
        else:
            self.dismiss(input_widget.value)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(False)
