# -*- coding: utf-8 -*-


import inflect
from textual.widgets import (
    Placeholder,
)

from ..data_analyzers.context import ctx
from ..general_widgets.custom_general_widgets import FocusLabel
from ..templates.item_selection_modal import ItemSelectionModal
from ..templates.model_template import ModelTemplate
from ..templates.selection_template import SelectionTemplate
from .atlas_based import AtlasBased
from .dual_reg import DualReg
from .falff import Falff
from .preproc_output import PreprocessedOutputOptions
from .reho import ReHo
from .seed_based import SeedBased
from .task_based import TaskBased

p = inflect.engine()
ITEM_MAP = {
    "task_based": "Task-based",
    "seed_based_connectivity": "Seed-based connectivity",
    "dual_regression": "Dual regression",
    "atlas_based_connectivity": "Atlas-based connectivity matrix",
    "reho": "ReHo",
    "falff": "fALFF",
    "preprocessed_image": "Output preprocessed image",
}
ITEM_KEY = "features"
SETTING_KEY = "settings"


class FeatureSelectionModal(ItemSelectionModal):
    ITEM_MAP = ITEM_MAP
    ITEM_KEY = ITEM_KEY


class FeatureSelection(SelectionTemplate):
    """
    FeatureSelection(Widget)
    A widget for feature selection, allowing users to add, rename, duplicate, delete, and sort features.

    Attributes
    ----------
    BINDINGS : list
        A list of binding tuples for feature actions.
    current_order : list
        A list defining the default order of features.

    Methods
    -------
    __init__(self, disabled=False, **kwargs) -> None
        Each created widget needs to have a unique id, even after deletion it cannot be recycled.
        The id_counter takes care of this and feature_items dictionary keeps track of the id number and feature name.

    compose(self) -> ComposeResult
        Generates the layout of the widget, including the sidebar with buttons and a content switcher.

    on_mount(self) -> None
        Sets the initial border title of the content switcher to "First-level features".

    on_list_view_selected(self, event: ListView.Selected) -> None
        Changes border title color according to the feature type.

    add(self) -> None
        Binds the "Add" button to the add_item action.

    delete(self) -> None
        Binds the "Delete" button to the delete_feature action.

    rename(self) -> None
        Pops up a screen to set the new feature name. Afterwards the dictionary entry is also renamed.

    duplicate(self) -> None
        Binds the "Duplicate" button to the duplicate_feature action.

    sort(self) -> None
        Binds the "Sort" button to the sort_features action.

    action_add_item(self) -> None
        Pops out the feature type selection windows and then uses add_new_item function to mount a new feature widget.

    add_new_item(self, new_item: tuple | bool) -> None
        Adds a new feature by mounting a new widget and creating a new entry in the dictionary to keep track of selections.

    action_delete_feature(self) -> None
        Unmount the feature and delete its entry from dictionaries.

    action_duplicate_feature(self)
        Duplicates the feature by a deep copy of the dictionary entry and then mounts a new widget while loading defaults from
        this copy.
    """

    ITEM_MAP = ITEM_MAP
    ITEM_KEY = ITEM_KEY
    SETTING_KEY = SETTING_KEY

    def on_focus_label_selected(self, message: FocusLabel.Selected) -> None:
        """Changes border title color according to the feature type."""

        # Update content switcher with the newly selected id.
        # list ids have suffix _flabel, so to match the widget in the content switcher we need to remove this suffix
        content_switcher_item_new_id = message.control.id[:-7]
        current_feature = self.feature_items[content_switcher_item_new_id]

        # Use currently selected switcher id to grab the focus label so that we can deselect it.
        content_switcher_item_old_id = self.get_widget_by_id("content_switcher").current
        # when we delete item, it can be also a None
        if content_switcher_item_old_id is not None and content_switcher_item_old_id != content_switcher_item_new_id:
            collapsible_item_old_id = content_switcher_item_old_id + "_flabel"
            self.get_widget_by_id(collapsible_item_old_id).deselect()

        self.get_widget_by_id("content_switcher").current = content_switcher_item_new_id
        self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
            self.ITEM_MAP[current_feature.type], current_feature.name
        )
        self.get_widget_by_id("content_switcher").styles.border_title_color = "white"

    def on_mount(self) -> None:
        self.get_widget_by_id("content_switcher").border_title = "First-level features"

    def action_add_item(self) -> None:
        """Pops out the feature type selection windows and then uses add_new_item function to mount a new feature
        widget."""
        occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]
        self.app.push_screen(
            FeatureSelectionModal(occupied_feature_names),
            self.add_new_item,
        )

    def fill_cache_and_create_new_content_item(self, new_item):
        item_type, item_name = new_item
        content_switcher_item_new_id = p.singular_noun(self.ITEM_KEY) + "_item_" + str(self._id_counter)

        if item_name not in ctx.cache:
            if item_type == "preprocessed_image":
                ctx.cache[item_name]["settings"]["name"] = item_name
                ctx.cache[item_name]["settings"]["output_image"] = True
            else:
                ctx.cache[item_name]["features"]["name"] = item_name
                ctx.cache[item_name]["features"]["setting"] = item_name + "Setting"
                ctx.cache[item_name]["settings"]["name"] = item_name + "Setting"

        item_type_class: type[ModelTemplate] | None = {
            "task_based": TaskBased,
            "seed_based_connectivity": SeedBased,
            "dual_regression": DualReg,
            "atlas_based_connectivity": AtlasBased,
            "preprocessed_image": PreprocessedOutputOptions,
            "reho": ReHo,
            "falff": Falff,
        }.get(item_type)

        if item_type_class is not None:
            new_content_item = item_type_class(
                this_user_selection_dict=ctx.cache[item_name],
                id=content_switcher_item_new_id,
                classes=p.singular_noun(self.ITEM_KEY),
            )
        else:
            new_content_item = Placeholder(str(self._id_counter), id=content_switcher_item_new_id, classes=item_type)
        return new_content_item
