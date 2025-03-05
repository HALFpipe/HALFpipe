# -*- coding: utf-8 -*-


import inflect
from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, ListView, OptionList
from textual.widgets.option_list import Option, Separator

from ..feature_widgets.base import FeatureNameInput, SelectionTemplate
from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.draggable_modal_screen import DraggableModalScreen
from .models import InterceptOnlyModel, LinearModel

p = inflect.engine()

ITEM_MAP = {"me": "Intercept-only", "lme": "Linear model"}


class GroupLevelModelSelectionScreen(DraggableModalScreen):
    """
    modelSelectionScreen
    ----------------------
    A class to create a draggable modal screen for selecting models. It extends from DraggableModalScreen and is used to
    present a list of models from which the first level model can be chosen.

    Attributes
    ----------
    CSS_PATH : str
        The path to the CSS stylesheet used for this screen.
    occupied_item_names : list
        List of model names that are already occupied.
    option_list : OptionList
        An option list to display the available model choices.
    title_bar : TitleBar
        The title bar displaying the title of the screen.

    Methods
    -------
    __init__(occupied_item_names) -> None
        Initializes the modelSelectionScreen with occupied model names and sets up the option list.
    on_mount() -> None
        Mounts the option list and the Cancel button to the screen.
    on_option_list_option_selected(message: OptionList.OptionSelected) -> None
        Handles the event where an option from the option list is selected, prompting the user to input a model name.
    key_escape(self)
        Handles the escape action when the Cancel button is pressed, dismissing the screen without making a selection.
    """

    CSS_PATH = "tcss/group_level_selection_screen.tcss"

    def __init__(self, occupied_names) -> None:
        self.occupied_names = occupied_names
        super().__init__()
        # Temporary workaround because some bug in Textual between versions 0.70 and 0.75.
        self.option_list = OptionList(
            Separator(),
            Option("Intercept only", id="me"),
            Separator(),
            Option("Linear model", id="lme"),
            Separator(),
            id="options",
        )

        self.title_bar.title = "Specify model type"

    def on_mount(self) -> None:
        self.content.mount(self.option_list, Horizontal(Button("Cancel", id="cancel_button"), id="botton_container"))

    def on_option_list_option_selected(self, message: OptionList.OptionSelected) -> None:
        def get_selection_name(selection_name: str | None) -> None:
            if selection_name is not None:
                self.dismiss((message.option.id, selection_name))

        self.app.push_screen(
            FeatureNameInput(self.occupied_names),
            get_selection_name,
        )

    @on(Button.Pressed, "#cancel_button")
    def key_escape(self):
        self.dismiss(False)


class ModelItem:
    """
    FeatureItem class to represent a feature with a type and name.

    Attributes
    ----------
    type : str
        The type of the feature.
    name : str
        The name of the feature.
    """

    def __init__(self, _type, name):
        self.type = _type
        self.name = name


class GroupLevelModelSelection(SelectionTemplate):
    """This is for group level models"""

    ITEM_MAP = ITEM_MAP
    # content_type = 'model'
    ITEM_KEY = "models"

    def on_mount(self) -> None:
        self.get_widget_by_id("content_switcher").border_title = "Group-level models"

    def action_add_item(self) -> None:
        """Pops out the model type selection windows and then uses add_new_item function to mount a new model
        widget."""
        occupied_item_names = [self.feature_items[item].name for item in self.feature_items]
        self.app.push_screen(
            GroupLevelModelSelectionScreen(occupied_item_names),
            self.add_new_item,
        )

    def fill_cache_and_create_new_content_item(self, new_item):
        item_type, item_name = new_item
        content_switcher_item_new_id = p.singular_noun(self.ITEM_KEY) + "_item_" + str(self._id_counter)

        if item_name not in ctx.cache:
            ctx.cache[item_name]["models"]["name"] = item_name

        item_type_class: type = {
            "me": InterceptOnlyModel,
            "lme": LinearModel,
        }.get(item_type)

        if item_type_class is not None:
            new_content_item = item_type_class(
                this_user_selection_dict=ctx.cache[item_name],
                id=content_switcher_item_new_id,
                classes=p.singular_noun(self.ITEM_KEY),
            )
        return new_content_item

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Changes border title color according to the feature type."""
        current_id = event.item.id
        current_feature = self.feature_items[current_id]
        self.get_widget_by_id("content_switcher").current = current_id
        self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
            self.ITEM_MAP[current_feature.type], current_feature.name
        )
        self.get_widget_by_id("content_switcher").styles.border_title_color = "white"

    def action_delete_item(self) -> None:
        """Unmount the feature and delete its entry from dictionaries, including aggregate models."""
        self.app.push_screen(Confirm(), lambda respond: self._delete_item(respond, check_aggregate=True))
