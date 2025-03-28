# -*- coding: utf-8 -*-


import inflect
from textual.widgets import ListView

from ..data_analyzers.context import ctx
from ..specialized_widgets.confirm_screen import Confirm
from ..templates.item_selection_modal import ItemSelectionModal
from ..templates.model_template import ModelTemplate
from ..templates.selection_template import SelectionTemplate
from .intercept_only_model import InterceptOnlyModel
from .linear_model import LinearModel

p = inflect.engine()

# A mapping of model type keys to their display names.
ITEM_MAP = {"me": "Intercept-only", "lme": "Linear model"}
# The key used to identify models in the application's data structures.
ITEM_KEY = "models"


class GroupLevelModelSelectionModal(ItemSelectionModal):
    """
    A modal for selecting a group-level model type.

    This class extends `ItemSelectionModal` to provide a modal dialog
    specifically for selecting the type of group-level model to add.

    Attributes
    ----------
    ITEM_MAP : dict[str, str]
        A mapping of model type keys to their display names.
    ITEM_KEY : str
        The key used to identify models in the application's data structures.
    """

    ITEM_MAP = ITEM_MAP
    ITEM_KEY = ITEM_KEY


class GroupLevelModelSelection(SelectionTemplate):
    """
    A widget for managing the selection and configuration of group-level models.

    This class extends `SelectionTemplate` to provide a widget that allows
    users to add, delete, and configure group-level models. It manages a
    list of models, each of which can be an intercept-only model or a
    linear model.

    Attributes
    ----------
    ITEM_MAP : dict[str, str]
        A mapping of model type keys to their display names.
    ITEM_KEY : str
        The key used to identify models in the application's data structures.

    Methods
    -------
    on_mount()
        Sets the border title for the content switcher.
    action_add_item()
        Pops up a modal to select a model type and then adds a new model widget.
    fill_cache_and_create_new_content_item(new_item)
        Creates a new model widget and fills the cache with its data.
    on_list_view_selected(event)
        Updates the border title and color of the content switcher when a model is selected.
    action_delete_item()
        Pops up a confirmation dialog and then deletes the selected model.
    """

    ITEM_MAP = ITEM_MAP
    ITEM_KEY = ITEM_KEY

    def on_mount(self) -> None:
        self.get_widget_by_id("content_switcher").border_title = "Group-level models"

    def action_add_item(self) -> None:
        """Pops out the model type selection windows and then uses add_new_item function to mount a new model
        widget."""
        occupied_item_names = [self.feature_items[item].name for item in self.feature_items]
        self.app.push_screen(
            GroupLevelModelSelectionModal(occupied_item_names),
            self.add_new_item,
        )

    def fill_cache_and_create_new_content_item(self, new_item):
        item_type, item_name = new_item
        content_switcher_item_new_id = p.singular_noun(self.ITEM_KEY) + "_item_" + str(self._id_counter)

        if item_name not in ctx.cache:
            ctx.cache[item_name]["models"]["name"] = item_name

        item_type_class: type[ModelTemplate] | None = {
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
