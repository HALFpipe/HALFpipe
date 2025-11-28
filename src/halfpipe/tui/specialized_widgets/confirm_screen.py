# -*- coding: utf-8 -*-
from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, Static

from ..general_widgets.draggable_modal_screen import DraggableModalScreen


class Confirm(DraggableModalScreen):
    """
    A modal dialog for confirming an action with customizable buttons.

    This class provides a modal dialog that prompts the user with a
    message and up to two buttons ("Ok" and "Cancel"). It allows
    customization of the button texts, button variants, and the message
    content. It can also be configured to display only one button.

    Attributes
    ----------
    CSS_PATH : list[str]
        Path to the CSS file for styling the modal.

    Methods
    -------
    __init__(
        text,
        left_button_text,
        right_button_text,
        left_button_variant,
        right_button_variant,
        title,
        id,
        classes,
        width,
        message_widget,
    )
        Initializes the Confirm modal with provided parameters.
    on_resize()
        Adjusts the width of the message widget based on the container's size.
    on_mount()
        Mounts the message widget and buttons to the modal content.
    ok()
        Handles the event when the "Ok" button is pressed.
    cancel()
        Handles the event when the "Cancel" button is pressed.
    key_escape()
        Handles the event when the Escape key is pressed.
    request_close()
        Handles the event when the close button is pressed.
    _confirm_window()
        Dismisses the modal and returns True.
    """

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
        message_widget=Static,
        extra_button_text=None,
    ) -> None:
        """
        Initializes the Confirm modal with provided parameters.

        Parameters
        ----------
        text : str, optional
            The message to be displayed in the modal, by default "Are you sure?".
        left_button_text : str | bool, optional
            The text for the left button, or False to hide it, by default "Ok".
        right_button_text : str | bool, optional
            The text for the right button, or False to hide it, by default "Cancel".
        left_button_variant : str, optional
            The variant for the left button (e.g., "success"), by default "success".
        right_button_variant : str, optional
            The variant for the right button (e.g., "error"), by default "error".
        title : str, optional
            The title of the modal window, by default "".
        id : str | None, optional
            The unique identifier for the modal, by default None.
        classes : str | None, optional
            Additional CSS classes to apply to the modal, by default None.
        width : int | None, optional
            The width of the modal, by default None.
        message_widget : type[Static], optional
            The widget class to use for displaying the message, by default Static.
        """
        super().__init__(id=id, classes=classes)
        # The message to be displayed in the modal.
        # self.text = text
        # The title of the modal window.
        self.title_bar.title = title
        # The widget class to use for displaying the message.
        self.message_widget = message_widget(text, id="message")
        # this here allows to use the modal just with one button, either outputting True or False (left/right)
        # use button_text = False to disable the button
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
        self.extra_button = False
        if extra_button_text is not None:
            self.buttons.append(Button(extra_button_text, classes="button extra", id="extra_button"))
            self.extra_button = True

    def on_resize(self):
        """
        Adjusts the width of the message widget based on the container's size.

        This method is called when the modal is resized. It adjusts the
        width of the message widget to fit within the modal's container.
        """
        self.message_widget.styles.width = (
            self.get_widget_by_id("draggable_modal_screen_container_wrapper").container_size.width - 2
        )

    def on_mount(self) -> None:
        """
        Mounts the message widget and buttons to the modal content.

        This method is called when the modal is mounted. It sets up the
        layout by adding the message widget and action buttons.
        """
        self.content.mount(
            self.message_widget,
            Horizontal(
                *self.buttons,
                classes="button_grid",
            ),
        )

    @on(Button.Pressed, ".button_grid .ok")
    def ok(self):
        """
        Handles the event when the "Ok" button is pressed.

        This method is called when the user presses the "Ok" button. It
        calls `_confirm_window` to dismiss the modal with a value of True.
        """
        self._confirm_window()

    @on(Button.Pressed, ".button_grid .cancel")
    def cancel(self):
        """
        Handles the event when the "Cancel" button is pressed.

        This method is called when the user presses the "Cancel" button.
        It calls `request_close` to dismiss the modal with a value of
        False.
        """
        # self.request_close()
        # Clicking on the 'X' in the draggable window bar, escape key and the close button must always yield the same dismiss
        # value!
        if self.active_index == 0:  # default button is the 'Ok' button
            self.dismiss(True)
        else:  # default button is the 'Cancel' button or we have bot buttons
            self.dismiss(False)

    @on(Button.Pressed, "#extra_button")
    def on_extra_button_pressed(self):
        """
        Handles the event when the "Cancel" button is pressed.

        This method is called when the user presses the "Cancel" button.
        It calls `request_close` to dismiss the modal with a value of
        False.
        """
        self.dismiss(None)

    def key_escape(self):
        """
        Handles the event when the Escape key is pressed.

        This method is called when the user presses the Escape key. It
        calls `request_close` to dismiss the modal with a value of
        False.
        """
        self.request_close()

    def _confirm_window(self):
        """
        Dismisses the modal and returns True.

        This method is called when the user confirms the action. It
        dismisses the modal with a value of True.
        """
        self.dismiss(True)

    def request_close(self):
        """
        Handles the event when the close button is pressed.

        This method is called when the user attempts to close the modal
        window. It dismisses the modal with a value of True or False
        depending on the active button.
        """
        # Clicking on the 'X' in the draggable window bar, escape key and the close button must always yield the same dismiss
        # value!
        if self.active_index == 0:  # default button is the 'Ok' button
            self.dismiss(True)
        elif self.extra_button:
            self.dismiss(None)
        else:  # default button is the 'Cancel' button or we have bot buttons
            self.dismiss(False)


class SimpleMessageModal(Confirm):
    """
    A simple message modal dialog with a customizable message and title.

    This class extends `Confirm` to provide a modal dialog that displays
    a message and a single "Close" button. It is used for displaying
    simple informational messages to the user.

    Parameters
    ----------
    text : str
        The message to be displayed in the modal.
    title : str, optional
        The title of the modal window, by default "".
    id : str | None, optional
        The unique identifier for the modal, by default None.
    classes : str | None, optional
        Additional CSS classes to apply to the modal, by default None.
    """

    def __init__(self, text, title="", id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the SimpleMessageModal.

        Parameters
        ----------
        text : str
            The message to be displayed in the modal.
        title : str, optional
            The title of the modal window, by default "".
        id : str | None, optional
            The unique identifier for the modal, by default None.
        classes : str | None, optional
            Additional CSS classes to apply to the modal, by default None.
        """
        super().__init__(
            text=text,
            title=title,
            id=id,
            classes=classes,
            left_button_text=False,
            right_button_text="Close",
            right_button_variant="default",
            message_widget=Static,
        )
