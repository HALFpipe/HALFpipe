# -*- coding: utf-8 -*-
from typing import List

from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, RadioButton, RadioSet, Static

from ..general_widgets.draggable_modal_screen import DraggableModalScreen


class SelectionModal(DraggableModalScreen):
    """
    A modal dialog for making a single selection from a set of options.

    This class provides a modal dialog that presents the user with a set of
    radio buttons to choose from. It can be configured with custom options,
    a title, and instructions. It supports both an "OK" and a "Cancel" button,
    or just an "OK" button for mandatory selections.

    Parameters
    ----------
    options : dict[str, str], optional
        A dictionary where keys are option identifiers and values are the
        display text for each option. Defaults to {"a": "A", "b": "B"}.
    title : str, optional
        The title of the modal window, by default "".
    instructions : str, optional
        Instructions or description to be displayed at the top of the
        modal window, by default "Select".
    only_ok_button : bool, optional
        If True, only an "OK" button is displayed, making a selection
        mandatory, by default False.
    id : str, optional
        An optional identifier for the modal window, by default None.
    classes : str, optional
        An optional string of classes for applying styles to the modal
        window, by default None.

    Attributes
    ----------
    title_bar.title : str
        Sets the title of the modal window.
    instructions : str
        Holds the instruction text for the modal window.
    widgets_to_mount : list[Widget]
        A list of widgets to be mounted on the modal window, including
        title, radio buttons, and OK/Cancel buttons.
    choice : str | bool
        The selected choice from the radio buttons, or False if canceled.

    Methods
    -------
    on_mount()
        Called when the window is mounted. Mounts the content widgets.
    _on_ok_button_pressed()
        Handles the OK button press event, dismissing the modal window
        with the current choice.
    _on_cancel_button_pressed()
        Handles the Cancel button press event, dismissing the modal
        window with False value.
    _on_radio_set_changed(event)
        Handles the event when the radio button selection changes.
        Updates the choice attribute with the selected option key.
    request_close()
        Handles the event when the close button is pressed.
    """

    DEFAULT_CSS = """
        SelectionModal {
            #draggable_modal_screen_container_wrapper {
                width: 81;
                background: black;
            }
            RadioSet {
                height: auto;
                width: auto;
            }
            Horizontal {
                height: 4;
                width: 100%;
                align: right bottom;
                offset-x: 0;
                Button {
                    margin: 0 1;
                }
            }
            #title {
                content-align: center middle;
                text-style: bold;
                content-align: center middle;
                text-align: center;
                width: auto;
                margin: 1 1 0 1;
            }
        }
    """

    def __init__(
        self,
        options=None | dict,
        title="",
        instructions="Select",
        only_ok_button: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initializes the SelectionModal.

        Parameters
        ----------
        options : dict[str, str], optional
            A dictionary where keys are option identifiers and values are the
            display text for each option. Defaults to {"a": "A", "b": "B"}.
        title : str, optional
            The title of the modal window, by default "".
        instructions : str, optional
            Instructions or description to be displayed at the top of the
            modal window, by default "Select".
        only_ok_button : bool, optional
            If True, only an "OK" button is displayed, making a selection
            mandatory, by default False.
        id : str, optional
            An optional identifier for the modal window, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the modal
            window, by default None.
        """
        super().__init__(id=id, classes=classes)
        self.title_bar.title = title
        self.instructions = instructions
        RadioButton.BUTTON_INNER = "X"
        self.options: dict = {"a": "A", "b": "B"} if options is None else options

        # In some cases the user just must made some choice in the selection. In particular this is the case when one is
        # some of the Meta classes (CheckMeta...) are in action. Returning from this stage by hitting the cancel button would
        # not make sense.
        self.only_ok_button = only_ok_button
        if only_ok_button is True:
            button_panel = Horizontal(Button("OK", id="ok"))
        else:
            button_panel = Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel"))

        self.widgets_to_mount = [
            Static(self.instructions, id="title"),
            RadioSet(*[RadioButton(self.options[key], value=i == 0) for i, key in enumerate(self.options)], id="radio_set"),
            button_panel,
        ]

    def on_mount(self) -> None:
        """Called when the window is mounted."""
        self.content.mount(*self.widgets_to_mount)

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        choice = list(self.options.keys())[self.get_widget_by_id("radio_set")._selected]
        self.dismiss(choice)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(False)

    def request_close(self):
        if self.only_ok_button is True:
            choice = list(self.options.keys())[self.get_widget_by_id("radio_set")._selected]
            self.dismiss(choice)
        else:
            self.dismiss(False)


class DoubleSelectionModal(SelectionModal):
    """
    A modal dialog for making two selections from two sets of radio buttons.

    This class extends `SelectionModal` to provide a modal dialog that
    presents the user with two sets of radio buttons to choose from. It
    can be configured with custom options, a title, and instructions for
    each set of radio buttons.

    Parameters
    ----------
    options : list[dict[str, str]], optional
        A list containing two dictionaries where the keys are the unique
        identifiers and the values are the corresponding option labels to
        display in the radio buttons.
    title : str, optional
        The title of the modal dialog, by default "".
    instructions : list[str], optional
        A list containing two instructions, to be displayed above each set
        of radio buttons.
    id : str, optional
        The unique identifier for the modal, by default None.
    classes : str, optional
        The CSS classes to apply to the modal, by default None.

    Attributes
    ----------
    choice : list[str | bool]
        A list containing the selected options from each radio set, or
        False if canceled.

    Methods
    -------
    _on_radio_set_changed(event)
        Updates the internal choice state when a radio button selection is
        changed.
    """

    DEFAULT_CSS = """
        DoubleSelectionModal {
            Static {
                padding: 0 1;
            }
            #draggable_modal_screen_container_wrapper {
                width: 50;
                height: 18;
                background: black;
            }
            RadioSet {
                height: 4;
                width: 48;
            }
        }
        """

    def __init__(self, options=None, title="", instructions=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(title=title, id=id, classes=classes)
        self.instructions = instructions
        self.options: dict = options
        self.choice: List[str] = ["default_choice??? todo", "1"]
        self.widgets_to_mount = [
            Static(self.instructions[0], id="title_0"),
            RadioSet(*[RadioButton(self.options[0][key]) for key in self.options[0]], id="radio_set_0"),
            Static(self.instructions[1], id="title_1"),
            RadioSet(*[RadioButton(self.options[1][key]) for key in self.options[1]], id="radio_set_1"),
            Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
        ]

    def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.control.id == "radio_set_0":
            self.choice[0] = list(self.options[0].keys())[event.index]
        if event.control.id == "radio_set_1":
            self.choice[1] = list(self.options[1].keys())[event.index]
