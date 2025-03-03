# -*- coding: utf-8 -*-
# ok to review

import copy

import inflect
import numpy as np
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import (
    Button,
    Collapsible,
    ContentSwitcher,
    Input,
    OptionList,
    Placeholder,
)
from textual.widgets.option_list import Option, Separator

from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.custom_general_widgets import FocusLabel
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.utils import widget_exists
from .features import AtlasBased, DualReg, Falff, PreprocessedOutputOptions, ReHo, SeedBased, TaskBased

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

FEATURES_MAP_colors = {
    "task_based": "crimson",
    "seed_based_connectivity": "silver",
    "dual_regression": "ansi_bright_cyan",
    "atlas_based_connectivity": "blueviolet",
    "reho": "slategray",
    "falff": "magenta",
    "preprocessed_image": "white",
}


class FeatureNameInput(DraggableModalScreen):
    """
    FeatureNameInput Class for a Draggable Modal Screen input interface.

    Attributes
    ----------
    CSS_PATH : list
        The CSS paths used by the class.

    Methods
    -------
    __init__(occupied_feature_names)
        Initializes the FeatureNameInput class with occupied feature names.

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

    CSS_PATH = ["tcss/feature_name_input.tcss"]

    def __init__(self, occupied_feature_names) -> None:
        #   self.top_parent = top_parent
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
                    #  left_button_variant=None,
                    right_button_variant="default",
                    title="Existing name",
                    classes="confirm_error",
                )
            )
        else:
            self.dismiss(feature_name)

    def _cancel_window(self):
        self.dismiss(None)


class FeatureSelectionScreen(DraggableModalScreen):
    """
    FeatureSelectionScreen
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
        Initializes the FeatureSelectionScreen with occupied feature names and sets up the option list.
    on_mount() -> None
        Mounts the option list and the Cancel button to the screen.
    on_option_list_option_selected(message: OptionList.OptionSelected) -> None
        Handles the event where an option from the option list is selected, prompting the user to input a feature name.
    key_escape(self)
        Handles the escape action when the Cancel button is pressed, dismissing the screen without making a selection.
    """

    ITEM_MAP = ITEM_MAP
    CSS_PATH = "tcss/feature_selection_screen.tcss"

    def __init__(self, occupied_feature_names) -> None:
        #    self.top_parent = top_parent
        self.occupied_feature_names = occupied_feature_names
        super().__init__()
        # Temporary workaround because some bug in Textual between versions 0.70 and 0.75.
        self.option_list = OptionList(
            Option(self.ITEM_MAP["task_based"], id="task_based"),
            Separator(),
            Option(self.ITEM_MAP["seed_based_connectivity"], id="seed_based_connectivity"),
            Separator(),
            Option(self.ITEM_MAP["dual_regression"], id="dual_regression"),
            Separator(),
            Option(self.ITEM_MAP["atlas_based_connectivity"], id="atlas_based_connectivity"),
            Separator(),
            Option(self.ITEM_MAP["reho"], id="reho"),
            Separator(),
            Option(self.ITEM_MAP["falff"], id="falff"),
            Separator(),
            Option(self.ITEM_MAP["preprocessed_image"], id="preprocessed_image"),
            Separator(),
            id="options",
        )
        # self.option_list = OptionList(id="options")
        # for f in ITEM_MAP:
        #     # option_list = self.get_widget_by_id("options")
        #     self.option_list.add_option(Option(ITEM_MAP[f], id=f))
        #     self.option_list.add_option(Separator())

        self.title_bar.title = "Choose first level feature"

    def on_mount(self) -> None:
        self.content.mount(self.option_list, Horizontal(Button("Cancel", id="cancel_button"), id="botton_container"))

    def on_option_list_option_selected(self, message: OptionList.OptionSelected) -> None:
        def get_feature_name(feature_name: str | None) -> None:
            if feature_name is not None:
                self.dismiss((message.option.id, feature_name))

        self.app.push_screen(
            FeatureNameInput(self.occupied_feature_names),
            get_feature_name,
        )

    @on(Button.Pressed, "#cancel_button")
    def key_escape(self):
        self.dismiss(False)


class FeatureItem:
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


class SelectionTemplate(Widget):
    ITEM_MAP = ITEM_MAP
    BINDINGS = [("a", "add_item", "Add"), ("d", "delete_feature", "Delete")]
    current_order = ["name", "type"]
    # content_type = ''
    ITEM_KEY: None | str = None  # To be defined in child classes
    SETTING_KEY: None | str = None  # Optional, only used in some child classes

    def __init__(self, disabled=False, **kwargs) -> None:
        """Each created widget needs to have a unique id, even after deletion it cannot be recycled.
        The id_counter takes care of this and feature_items dictionary keeps track of the id number and feature name.
        """
        super().__init__(disabled=disabled, **kwargs)
        # self.top_parent = app
        #   self.ctx = ctx
        # self.available_images = available_images
        #    ctx.cache = user_selections_dict
        self._id_counter = 0
        self.feature_items: dict = {}

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Grid(
                Button("New", variant="primary", classes="add_button"),
                Button("Rename", variant="primary", classes="rename_button"),
                Button("Duplicate", variant="primary", classes="duplicate_button"),
                Button("Delete", variant="primary", classes="delete_button"),
                Button("Sort", variant="primary", classes="sort_button"),
                classes="buttons",
            ),
            *[
                Collapsible(title=self.ITEM_MAP[f], id="list_" + f, classes="list", collapsed=False)
                for f in self.ITEM_MAP.keys()
            ],
            id="sidebar",
        )
        #  yield EventFilePanel()
        yield ContentSwitcher(id="content_switcher")

    @on(Button.Pressed, "#sidebar .add_button")
    async def add(self) -> None:
        await self.run_action("add_item")

    @on(Button.Pressed, "#sidebar .delete_button")
    async def delete(self) -> None:
        await self.run_action("delete_item")

    @on(Button.Pressed, "#sidebar .duplicate_button")
    async def duplicate(self) -> None:
        await self.run_action("duplicate_item")

    @on(Button.Pressed, "#sidebar .sort_button")
    async def sort(self) -> None:
        await self.run_action("sort_features")

    def _delete_item(self, respond: bool, check_aggregate: bool = False) -> None:
        """Common logic for deleting a feature or item."""
        if respond:
            current_content_switcher_item_id = self.get_widget_by_id("content_switcher").current
            current_collabsible_item_id = current_content_switcher_item_id + "_flabel"
            name = self.feature_items[current_content_switcher_item_id].name

            # Remove widgets
            self.get_widget_by_id(current_content_switcher_item_id).remove()
            self.get_widget_by_id(current_collabsible_item_id).remove()

            # Remove from feature_items and cache
            self.feature_items.pop(current_content_switcher_item_id)
            ctx.cache.pop(name)
            self.get_widget_by_id("content_switcher").current = None

            # Additional step for action_delete_feature
            if check_aggregate and name + "__aggregate_models_list" in ctx.cache:
                ctx.cache.pop(name + "__aggregate_models_list")

    def action_delete_item(self) -> None:
        """Unmount the feature and delete its entry from dictionaries, including aggregate models."""
        self.app.push_screen(Confirm(), lambda respond: self._delete_item(respond, check_aggregate=False))

    # def action_delete_item(self) -> None:
    #     """Unmount the feature and delete its entry from dictionaries."""
    #
    #     def confirmation(respond: bool):
    #         if respond:
    #             current_content_switcher_item_id = self.get_widget_by_id("content_switcher").current
    #             current_collabsible_item_id = current_content_switcher_item_id+'_flabel'
    #             name = self.feature_items[current_content_switcher_item_id].name
    #             self.get_widget_by_id(current_content_switcher_item_id).remove()
    #             self.get_widget_by_id(current_collabsible_item_id).remove()
    #             self.feature_items.pop(current_content_switcher_item_id)
    #             ctx.cache.pop(name)
    #             self.get_widget_by_id("content_switcher").current = None
    #
    #     self.app.push_screen(Confirm(), confirmation)

    def action_sort_features(self):
        """Sorting alphabetically and by feature type."""

        def sort_children(by):
            for i in range(len(self.feature_items.keys())):
                current_list_item_ids = [i.id for i in self.get_widget_by_id("list").children]
                item_names = [getattr(self.feature_items[i], by) for i in current_list_item_ids]
                correct_order = np.argsort(np.argsort(item_names))
                which_to_move = list(correct_order).index(np.int64(i))
                self.get_widget_by_id("list").move_child(int(which_to_move), before=int(i))

        sort_children(self.current_order[0])
        sort_children(self.current_order[1])
        self.current_order = [self.current_order[1], self.current_order[0]]

    async def add_new_item(self, new_item: tuple | bool) -> None:
        """Principle of adding a new feature lies in mounting a new widget while creating a new entry in the dictionary
        to keep track of the selections which are later dumped into the Context object.
        If this is a load or a duplication, then new entry is not created but read from the dictionary.
        The dictionary entry was created elsewhere.
        """
        if isinstance(new_item, tuple) or isinstance(new_item, list):
            item_type, item_name = new_item
            content_switcher_item_new_id = p.singular_noun(self.ITEM_KEY) + "_item_" + str(self._id_counter)
            collapsible_item_new_id = content_switcher_item_new_id + "_flabel"

            self.feature_items[content_switcher_item_new_id] = FeatureItem(item_type, item_name)

            # the pseudo class here is to set a particular text color in the left panel
            # new_list_item = ListItem(
            #     Label(item_name, id=new_id, classes="labels " + item_type),
            #     id=new_id,
            #     classes="items",
            # )

            new_content_item = self.fill_cache_and_create_new_content_item(new_item)
            # Deselect previous FocusLabel if exists
            content_switcher_item_old_id = self.get_widget_by_id("content_switcher").current
            if content_switcher_item_old_id is not None:
                collapsible_item_old_id = content_switcher_item_old_id + "_flabel"
                if widget_exists(self, collapsible_item_old_id):
                    self.get_widget_by_id(collapsible_item_old_id).deselect()

            item_key = self.feature_items[content_switcher_item_new_id].type
            new_list_item = FocusLabel(item_name, id=collapsible_item_new_id)  # classes="labels " + item_type)
            await self.get_widget_by_id("list_" + item_key).query_one(Collapsible.Contents).mount(new_list_item)
            self.get_widget_by_id("list_" + item_key).collapsed = False
            await self.get_widget_by_id("content_switcher").mount(new_content_item)
            self.get_widget_by_id("content_switcher").current = content_switcher_item_new_id
            self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
                self.ITEM_MAP[item_key],
                self.feature_items[content_switcher_item_new_id].name,
            )
            self._id_counter += 1

    async def action_duplicate_item(self):
        """Duplicate an item based on child class configuration."""
        if self.ITEM_KEY is None:
            raise NotImplementedError("Child class must define ITEM_KEY.")

        current_id = self.get_widget_by_id("content_switcher").current
        item_name = self.feature_items[current_id].name
        item_name_copy = item_name + "Copy"

        # Deep copy existing data
        ctx.cache[item_name_copy] = copy.deepcopy(ctx.cache[item_name])

        # Update copied dictionary with new name
        ctx.cache[item_name_copy][self.ITEM_KEY]["name"] = item_name_copy

        # Optional setting key update (only applies if SETTING_KEY is set)
        if self.SETTING_KEY:
            ctx.cache[item_name_copy][self.ITEM_KEY]["setting"] = item_name_copy + "Setting"
            ctx.cache[item_name_copy][self.SETTING_KEY]["name"] = item_name_copy + "Setting"

        # Add new item
        await self.add_new_item((ctx.cache[item_name_copy][self.ITEM_KEY]["type"], item_name_copy))

    @on(Button.Pressed, "#sidebar .rename_button")
    async def action_rename_item(self) -> None:
        """Pops up a screen to set the new feature name and renames the dictionary entry."""

        def rename_item(new_item_name: str) -> None:
            if new_item_name is not None:
                content_switcher_item_current_id = self.get_widget_by_id("content_switcher").current
                collapsible_item_current_id = content_switcher_item_current_id + "_flabel"

                old_feature_name = self.feature_items[content_switcher_item_current_id].name

                # Update feature name
                self.feature_items[content_switcher_item_current_id].name = new_item_name
                self.get_widget_by_id(collapsible_item_current_id).update(new_item_name)

                # Update the border title
                self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
                    self.ITEM_MAP[self.feature_items[content_switcher_item_current_id].type],
                    new_item_name,
                )

                # Move cache data
                ctx.cache[new_item_name] = ctx.cache.pop(old_feature_name)

                # Update the model and setting keys in the cache
                if self.ITEM_KEY is not None:
                    ctx.cache[new_item_name][self.ITEM_KEY]["name"] = new_item_name
                if self.SETTING_KEY and self.ITEM_KEY is not None:
                    ctx.cache[new_item_name][self.ITEM_KEY]["setting"] = new_item_name + "Setting"
                    ctx.cache[new_item_name][self.SETTING_KEY]["name"] = new_item_name + "Setting"

        if self.ITEM_KEY is None:
            raise NotImplementedError("Child class must define ITEM_KEY.")

        occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]
        await self.app.push_screen(
            FeatureNameInput(occupied_feature_names),
            rename_item,
        )


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

    # content_type = 'feature'
    ITEM_KEY = "features"
    SETTING_KEY = "settings"

    def on_focus_label_selected(self, message: FocusLabel.Selected) -> None:
        # def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Changes border title color according to the feature type."""

        # Update content switcher with the newly selected id.
        # current_id = event.item.id
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
        self.get_widget_by_id("content_switcher").styles.border_title_color = FEATURES_MAP_colors[current_feature.type]

    def on_mount(self) -> None:
        self.get_widget_by_id("content_switcher").border_title = "First-level features"

    # @on(Button.Pressed, "#sidebar .rename_button")
    # async def action_rename_item(self) -> None:
    #     """Pops up a screen to set the new feature name. Afterwards the dictionary entry is also renamed."""
    #
    #     def rename_item(new_item_name: str) -> None:
    #         if new_item_name is not None:
    #             content_switcher_item_current_id = self.get_widget_by_id("content_switcher").current
    #             collapsible_item_current_id = content_switcher_item_current_id + '_flabel'
    #
    #             old_feature_name = self.feature_items[content_switcher_item_current_id].name
    #
    #             self.feature_items[content_switcher_item_current_id].name = new_item_name
    #             # self.query_one("#" + currently_selected_id + " .labels").update(new_item_name)
    #             self.get_widget_by_id(collapsible_item_current_id).update(new_item_name)
    #             # self.get_widget_by_id(currently_selected_id).select()
    #
    #
    #             self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
    #                 self.ITEM_MAP[self.feature_items[content_switcher_item_current_id].type],
    #                 new_item_name,
    #             )
    #             ctx.cache[new_item_name] = ctx.cache.pop(old_feature_name)
    #             ctx.cache[new_item_name]["features"]["name"] = new_item_name
    #             ctx.cache[new_item_name]["features"]["setting"] = new_item_name + "Setting"
    #             ctx.cache[new_item_name]["settings"]["name"] = new_item_name + "Setting"
    #
    #     occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]
    #     await self.app.push_screen(
    #         FeatureNameInput(occupied_feature_names),
    #         action_rename_item,
    #     )

    def action_add_item(self) -> None:
        # Try here first the event files
        # setting_filter_step_instance = SettingFilterStep()
        # setting_filter_step_instance.run()
        #  events_type_instance = EventsTypeStep()
        #  events_type_instance.run()

        """Pops out the feature type selection windows and then uses add_new_item function to mount a new feature
        widget."""
        occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]
        self.app.push_screen(
            FeatureSelectionScreen(occupied_feature_names),
            self.add_new_item,
        )

    def fill_cache_and_create_new_content_item(self, new_item):
        item_type, item_name = new_item
        content_switcher_item_new_id = p.singular_noun(self.ITEM_KEY) + "_item_" + str(self._id_counter)

        if item_name not in ctx.cache:
            if item_type != "preprocessed_image":
                ctx.cache[item_name]["features"]["name"] = item_name
                ctx.cache[item_name]["features"]["setting"] = item_name + "Setting"
                ctx.cache[item_name]["settings"]["name"] = item_name + "Setting"
            else:
                ctx.cache[item_name]["settings"]["name"] = item_name + "UnfilteredSetting"
                ctx.cache[item_name]["settings"]["output_image"] = True
        item_type_class: type
        if item_type == "task_based":
            item_type_class = TaskBased
        elif item_type == "seed_based_connectivity":
            item_type_class = SeedBased
        elif item_type == "dual_regression":
            item_type_class = DualReg
        elif item_type == "atlas_based_connectivity":
            item_type_class = AtlasBased
        elif item_type == "preprocessed_image":
            item_type_class = PreprocessedOutputOptions
        elif item_type == "reho":
            item_type_class = ReHo
        elif item_type == "falff":
            item_type_class = Falff
        if item_type_class is not None:
            new_content_item = item_type_class(
                this_user_selection_dict=ctx.cache[item_name],
                id=content_switcher_item_new_id,
                classes=p.singular_noun(self.ITEM_KEY),
            )
        else:
            new_content_item = Placeholder(str(self._id_counter), id=content_switcher_item_new_id, classes=item_type)
        return new_content_item

    # async def action_duplicate_feature(self):
    #     """Duplicating feature by a deep copy of the dictionary entry and then mounting a new widget while
    #     loading defaults from this copy.
    #     """
    #     current_id = self.get_widget_by_id("content_switcher").current
    #     item_name = self.feature_items[current_id].name
    #     item_name_copy = item_name + "Copy"
    #     ctx.cache[item_name_copy] = copy.deepcopy(ctx.cache[item_name])
    #     ctx.cache[item_name_copy]["features"]["name"] = item_name_copy
    #     ctx.cache[item_name_copy]["features"]["setting"] = item_name_copy + "Setting"
    #     ctx.cache[item_name_copy]["settings"]["name"] = item_name_copy + "Setting"
    #     await self.add_new_item((ctx.cache[item_name_copy]["features"]["type"], item_name_copy))
