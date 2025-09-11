# -*- coding: utf-8 -*-


import inflect
from textual import on
from textual.containers import Horizontal
from textual.widgets import (
    Button,
    OptionList,
)
from textual.widgets.option_list import Option, Separator

from ..general_widgets.draggable_modal_screen import DraggableModalScreen
from .utils.name_input import NameInput

p = inflect.engine()


class ItemSelectionModal(DraggableModalScreen):
    """
    A modal screen for selecting an item type and providing a name.

    This class provides a draggable modal screen that allows users to
    select a type of item from a list and then provide a name for the
    selected item. It is designed to be used for selecting and naming
    features or group level models items.

    Attributes
    ----------
    ITEM_MAP : dict[str, str]
        A dictionary mapping item IDs to their display names. This should
        be defined in subclasses.
    ITEM_KEY : str
        A string representing the type of item being selected (e.g.,
        "feature"). This should be defined in subclasses.
    DEFAULT_CSS : str
        The default CSS styles for the modal screen.
    occupied_feature_names : list[str]
        A list of names that are already in use and cannot be selected.
    option_list : OptionList
        The list of options from which the user can select an item type.
    title_bar : TitleBar
        The title bar of the modal screen.

    Methods
    -------
    __init__(occupied_feature_names)
        Initializes the ItemSelectionModal.
    on_mount()
        Called when the modal is mounted.
    on_option_list_option_selected(message)
        Handles the selection of an option from the option list.
    key_escape()
        Handles the Escape key press event.
    """

    ITEM_MAP: dict[str, str] = {}
    ITEM_KEY = ""
    DEFAULT_CSS = """
        ItemSelectionModal {
            #draggable_modal_screen_container_wrapper {
                width: 50;
                height: auto;
                min-width: 50;
                min-height: 15;

                WindowTitleBar {
                    dock: top;
                }
            }
            OptionList {
                offset-y: 0;
                width: 100%;
                height: auto;
                text-style: bold;
            }
            Button {
                width: 10;
            }
            #botton_container {
                width: 100%;
                height: 5;

                align: center top;
            }
        }
    """

    def __init__(self, occupied_feature_names) -> None:
        """
        Initializes the ItemSelectionModal.

        Parameters
        ----------
        occupied_feature_names : list[str]
            A list of names that are already in use.
        """
        self.occupied_feature_names = occupied_feature_names
        super().__init__()
        # Temporary workaround because some bug in Textual between versions 0.70 and 0.75.
        options = []
        for key in self.ITEM_MAP:
            options.append(Option(self.ITEM_MAP[key], id=key))
            options.append(Separator())

        # Remove the last separator
        options.pop()
        self.option_list = OptionList(*options, id="options")

        self.title_bar.title = f"Choose {p.singular_noun(self.ITEM_KEY)} type"

    def on_mount(self) -> None:
        """
        Called when the modal is mounted.

        This method is called when the modal is mounted. It initializes
        the UI components, including the option list and the "Cancel"
        button.
        """
        self.content.mount(self.option_list, Horizontal(Button("Cancel", id="cancel_button"), id="botton_container"))

    @on(OptionList.OptionSelected, "#options")
    def on_option_list_option_selected(self, message: OptionList.OptionSelected) -> None:
        """
        Handles the selection of an option from the option list.

        This method is called when an option is selected from the
        `OptionList`. It prompts the user to input a name for the
        selected item type using the `NameInput` modal.

        Parameters
        ----------
        message : OptionList.OptionSelected
            The message object containing information about the selected
            option.
        """

        def get_item_name(feature_name: str | None) -> None:
            """
            Callback function to handle the name input from NameInput.

            This function is called when the `NameInput` modal is
            dismissed. It dismisses the `ItemSelectionModal` with the
            selected item type and the provided name.

            Parameters
            ----------
            feature_name : str | None
                The name provided by the user, or None if the user
                canceled the name input.
            """
            if feature_name is not None:
                self.dismiss((message.option.id, feature_name))

        self.app.push_screen(
            NameInput(self.occupied_feature_names),
            get_item_name,
        )

    @on(Button.Pressed, "#cancel_button")
    def key_escape(self):
        """
        Handles the Escape key press event.

        This method is called when the user presses the Escape key or the
        "Cancel" button. It dismisses the modal without making a
        selection.
        """
        self.dismiss(False)
