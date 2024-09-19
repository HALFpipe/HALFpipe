# -*- coding: utf-8 -*-
import copy

import numpy as np
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, ContentSwitcher, Input, Label, ListItem, ListView, OptionList, Placeholder
from textual.widgets.option_list import Option, Separator

from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.false_input_warning_screen import FalseInputWarning
from .task_based.atlas_based import AtlasBased
from .task_based.dual_reg import DualReg
from .task_based.preprocessed_image_output import PreprocessedOutputOptions
from .task_based.seed_based import SeedBased
from .task_based.taskbased import TaskBased

# from ...model.spec import SpecSchema


FEATURES_MAP = {
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


class FeatureNameInput(ModalScreen):
    """Modal screen where the user can type the name of the new widget (or when renaming)."""

    CSS_PATH = ["tcss/feature_name_input.tcss"]

    def __init__(self, occupied_feature_names) -> None:
        #   self.top_parent = top_parent
        self.occupied_feature_names = occupied_feature_names
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Container(
            Input(
                placeholder="Enter feature name",
                id="feature_name",
                classes="feature_name",
            ),
            Grid(
                Button("Ok", classes="button ok"),
                Button("Cancel", classes="button cancel"),
                classes="button_grid",
            ),
            id="feature_name_input_screen",
        )

    @on(Button.Pressed, "#feature_name_input_screen .ok")
    def ok(self):
        self._confirm_window()

    @on(Button.Pressed, "#feature_name_input_screen .cancel")
    def cancel(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        feature_name = self.get_widget_by_id("feature_name").value
        if feature_name == "":
            self.app.push_screen(FalseInputWarning("Enter the name!"))
        elif feature_name in self.occupied_feature_names:
            self.app.push_screen(FalseInputWarning("Name already exists!\nUse another one."))
        else:
            self.dismiss(feature_name)

    def _cancel_window(self):
        self.dismiss(None)


class FeatureSelectionScreen(DraggableModalScreen):
    """Modal screen where user selects type of the new feature."""

    CSS_PATH = "tcss/feature_selection_screen.tcss"

    def __init__(self, occupied_feature_names) -> None:
        #    self.top_parent = top_parent
        self.occupied_feature_names = occupied_feature_names
        super().__init__()
        self.option_list = OptionList(id="options")
        for f in FEATURES_MAP:
            # option_list = self.get_widget_by_id("options")
            self.option_list.add_option(Option(FEATURES_MAP[f], id=f))
            self.option_list.add_option(Separator())

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
    """This small class creates an object where the type and name of the features are stored.
    The object is used when sorting the features.
    """

    def __init__(self, _type, name):
        self.type = _type
        self.name = name


class FeatureSelection(Widget):
    BINDINGS = [("a", "add_feature", "Add"), ("d", "delete_feature", "Delete")]
    current_order = ["name", "type"]

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
            ListView(id="list", classes="list"),
            id="sidebar",
        )
        #  yield EventFilePanel()
        yield ContentSwitcher(id="content_switcher")

    def on_mount(self) -> None:
        self.get_widget_by_id("content_switcher").border_title = "First-level features"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Changes border title color according to the feature type."""
        current_id = event.item.id
        current_feature = self.feature_items[current_id]
        self.get_widget_by_id("content_switcher").current = current_id
        self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
            FEATURES_MAP[current_feature.type], current_feature.name
        )
        self.get_widget_by_id("content_switcher").styles.border_title_color = FEATURES_MAP_colors[current_feature.type]

    @on(Button.Pressed, "#sidebar .add_button")
    async def add(self) -> None:
        await self.run_action("add_feature")

    @on(Button.Pressed, "#sidebar .delete_button")
    async def delete(self) -> None:
        await self.run_action("delete_feature")

    @on(Button.Pressed, "#sidebar .rename_button")
    async def rename(self) -> None:
        """Pops up a screen to set the new feature name. Afterwards the dictionary entry is also renamed."""

        def action_rename_feature(new_feature_name: str) -> None:
            if new_feature_name is not None:
                currently_selected_id = self.get_widget_by_id("content_switcher").current
                old_feature_name = self.feature_items[currently_selected_id].name

                self.feature_items[currently_selected_id].name = new_feature_name
                self.query_one("#" + currently_selected_id + " .labels").update(new_feature_name)
                self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
                    FEATURES_MAP[self.feature_items[currently_selected_id].type],
                    old_feature_name,
                )
                ctx.cache[new_feature_name] = ctx.cache.pop(old_feature_name)
                ctx.cache[new_feature_name]["features"]["name"] = new_feature_name
                ctx.cache[new_feature_name]["features"]["setting"] = new_feature_name + "Setting"
                ctx.cache[new_feature_name]["settings"]["name"] = new_feature_name + "Setting"

        occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]
        await self.app.push_screen(
            FeatureNameInput(occupied_feature_names),
            action_rename_feature,
        )

    @on(Button.Pressed, "#sidebar .duplicate_button")
    async def duplicate(self) -> None:
        await self.run_action("duplicate_feature")

    @on(Button.Pressed, "#sidebar .sort_button")
    async def sort(self) -> None:
        await self.run_action("sort_features")

    def action_add_feature(self) -> None:
        # Try here first the event files
        # setting_filter_step_instance = SettingFilterStep()
        # setting_filter_step_instance.run()
        #  events_type_instance = EventsTypeStep()
        #  events_type_instance.run()

        """Pops out the feature type selection windows and then uses add_new_feature function to mount a new feature
        widget."""
        occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]
        self.app.push_screen(
            FeatureSelectionScreen(occupied_feature_names),
            self.add_new_feature,
        )

    async def add_new_feature(self, new_feature_item: list | bool) -> None:
        """Principle of adding a new feature lies in mounting a new widget while creating a new entry in the dictionary
        to keep track of the selections which are later dumped into the Context object.
        If this is a load or a duplication, then new entry is not created but read from the dictionary.
        The dictionary entry was created elsewhere.
        """
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "add_new_feature, feature_widgets")
        if new_feature_item is not False:
            feature_type, feature_name = new_feature_item
            new_id = "feature_item_" + str(self._id_counter)
            self.feature_items[new_id] = FeatureItem(feature_type, feature_name)
            new_list_item = ListItem(
                Label(feature_name, id=new_id, classes="labels " + feature_type),
                id=new_id,
                classes="items",
            )
            # this dictionary will contain all made choices
            if feature_name not in ctx.cache:
                if feature_type != "preprocessed_image":
                    ctx.cache[feature_name]["features"]["name"] = feature_name
                    ctx.cache[feature_name]["features"]["setting"] = feature_name + "Setting"
                    ctx.cache[feature_name]["settings"]["name"] = feature_name + "Setting"
                else:
                    ctx.cache[feature_name]["settings"]["name"] = feature_name + "Setting"
                    ctx.cache[feature_name]["settings"]["output_image"] = True
            if feature_type == "task_based":
                feature_type_class = TaskBased
            elif feature_type == "seed_based_connectivity":
                feature_type_class = SeedBased
            elif feature_type == "dual_regression":
                feature_type_class = DualReg
            elif feature_type == "atlas_based_connectivity":
                feature_type_class = AtlasBased
            elif feature_type == "preprocessed_image":
                feature_type_class = PreprocessedOutputOptions
            else:
                feature_type_class = None
            if feature_type_class is not None:
                new_content_item = feature_type_class(
                    this_user_selection_dict=ctx.cache[feature_name],
                    id=new_id,
                    classes="feature",
                )
            else:
                new_content_item = Placeholder(str(self._id_counter), id=new_id, classes=feature_type)
            await self.get_widget_by_id("list").mount(new_list_item)
            await self.get_widget_by_id("content_switcher").mount(new_content_item)
            self.get_widget_by_id("content_switcher").current = new_id
            self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
                FEATURES_MAP[self.feature_items[new_id].type],
                self.feature_items[new_id].name,
            )
            self.get_widget_by_id("content_switcher").styles.border_title_color = FEATURES_MAP_colors[feature_type]
            self._id_counter += 1

    # def add_new_preprocessed_image(self, feature_name: str) -> None:
    # """
    # In the preprocessed image output we do not use the 'feature
    # """
    # print(
    # "11111aaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "add_new_preprocessed_image", "preprocessed", ctx.cache
    # )
    # if feature_name is not None:
    # feature_type = "preprocessed_image"
    # new_id = "feature_item_" + str(self._id_counter)
    # self.feature_items[new_id] = FeatureItem(feature_type, feature_name)
    # new_list_item = ListItem(
    # Label(feature_name, id=new_id, classes="labels " + feature_type),
    # id=new_id,
    # classes="items",
    # )
    # print(
    # "22222aaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    # "add_new_preprocessed_image",
    # "preprocessed",
    # ctx.cache,
    # )

    # # this dictionary will contain all made choices
    # if feature_name not in ctx.cache:
    # #       self.user_selections_dict[feature_name]["features"]["name"] = feature_name
    # #       self.user_selections_dict[feature_name]["features"]["setting"] = feature_name + "Setting"
    # ctx.cache[feature_name]["settings"]["name"] = feature_name + "Setting"
    # ctx.cache[feature_name]["settings"]["output_image"] = True
    # print(
    # "33333aaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    # "add_new_preprocessed_image",
    # "preprocessed",
    # ctx.cache,
    # )

    # new_content_item = PreprocessedOutputOptions(
    # #                self.top_parent,
    # #                self.ctx,
    # #    self.available_images,
    # this_user_selection_dict=ctx.cache[feature_name],
    # id=new_id,
    # classes=feature_type,
    # )
    # print(
    # "33333bbbbbbbbbbbbbbbbbbbbbbbbbbb", "add_new_preprocessed_image", "preprocessed", ctx.cache
    # )
    # self.get_widget_by_id("list").mount(new_list_item)
    # self.get_widget_by_id("content_switcher").mount(new_content_item)
    # self.get_widget_by_id("content_switcher").current = new_id
    # self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
    # "Preprocessed output",
    # self.feature_items[new_id].name,
    # )
    # self.get_widget_by_id("content_switcher").styles.border_title_color = "red"
    # self._id_counter += 1
    # print("44444dddddddddddddddddddd", ctx.cache)

    def action_delete_feature(self) -> None:
        """Unmount the feature and delete its entry from dictionaries."""

        def confirmation(respond: bool):
            if respond:
                current_id = self.get_widget_by_id("content_switcher").current
                name = self.feature_items[current_id].name
                self.get_widget_by_id(current_id).remove()
                self.feature_items.pop(current_id)
                ctx.cache.pop(name)

        self.app.push_screen(Confirm(), confirmation)

    def action_duplicate_feature(self):
        """Duplicating feature by a deep copy of the dictionary entry and then mounting a new widget while
        loading defaults from this copy.
        """
        current_id = self.get_widget_by_id("content_switcher").current
        feature_name = self.feature_items[current_id].name
        feature_name_copy = feature_name + "Copy"
        ctx.cache[feature_name_copy] = copy.deepcopy(ctx.cache[feature_name])
        ctx.cache[feature_name_copy]["features"]["name"] = feature_name_copy
        ctx.cache[feature_name_copy]["features"]["setting"] = feature_name_copy + "Setting"
        ctx.cache[feature_name_copy]["settings"]["name"] = feature_name_copy + "Setting"
        self.add_new_feature([ctx.cache[feature_name_copy]["features"]["type"], feature_name_copy])

    def action_sort_features(self):
        """Sorting alphabetically and by feature type."""

        def sort_children(by):
            for i in range(len(self.feature_items.keys())):
                current_list_item_ids = [i.id for i in self.get_widget_by_id("list").children]
                item_names = [getattr(self.feature_items[i], by) for i in current_list_item_ids]
                correct_order = np.argsort(np.argsort(item_names))
                which_to_move = list(correct_order).index(i)
                self.get_widget_by_id("list").move_child(int(which_to_move), before=int(i))

        sort_children(self.current_order[0])
        sort_children(self.current_order[1])
        self.current_order = [self.current_order[1], self.current_order[0]]
