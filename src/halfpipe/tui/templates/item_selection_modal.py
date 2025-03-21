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
    ItemSelectionScreen
    ----------------------
    A class to create a draggable modal screen for selecting features. It extends from DraggableModalScreen and is used to
    present a list of features from which the first level feature can be chosen.

    Attributes
    ----------
    CSS_PATH : str
        The path to the CSS stylesheet used for this screen.
    occupied_feature_names : list
        List of feature names that are already occupied.
    option_list : OptionList
        An option list to display the available feature choices.
    title_bar : TitleBar
        The title bar displaying the title of the screen.

    Methods
    -------
    __init__(occupied_feature_names) -> None
        Initializes the ItemSelectionScreen with occupied feature names and sets up the option list.
    on_mount() -> None
        Mounts the option list and the Cancel button to the screen.
    on_option_list_option_selected(message: OptionList.OptionSelected) -> None
        Handles the event where an option from the option list is selected, prompting the user to input a feature name.
    key_escape(self)
        Handles the escape action when the Cancel button is pressed, dismissing the screen without making a selection.
    """

    ITEM_MAP: dict[str, str] = {}
    ITEM_KEY = ""
    DEFAULT_CSS = """
        ItemSelectionModal {
            #draggable_modal_screen_container_wrapper {
                width: 50;
                height: 23;
                min-width: 50;
                min-height: 15;

                WindowTitleBar {
                    dock: top;
                }
            }
            OptionList {
                offset-y: 0;
                width: 100%;
                height: 16;
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
        self.content.mount(self.option_list, Horizontal(Button("Cancel", id="cancel_button"), id="botton_container"))

    def on_option_list_option_selected(self, message: OptionList.OptionSelected) -> None:
        def get_item_name(feature_name: str | None) -> None:
            if feature_name is not None:
                self.dismiss((message.option.id, feature_name))

        self.app.push_screen(
            NameInput(self.occupied_feature_names),
            get_item_name,
        )

    @on(Button.Pressed, "#cancel_button")
    def key_escape(self):
        self.dismiss(False)
