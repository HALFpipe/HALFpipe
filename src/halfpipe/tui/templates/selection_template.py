# -*- coding: utf-8 -*-


import copy

import inflect
import numpy as np
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.widget import Widget
from textual.widgets import (
    Button,
    Collapsible,
    ContentSwitcher,
)

from ..specialized_widgets.confirm_screen import Confirm
from ..data_analyzers.context import ctx
from ..general_widgets.custom_general_widgets import FocusLabel
from ..help_functions import widget_exists
from .utils.name_input import NameInput

p = inflect.engine()


class TypeNameItem:
    """
    TypeNameItem class to represent a feature with a type and name.

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
    ITEM_MAP: dict[str, str] = {}
    BINDINGS = [("a", "add_item", "Add"), ("d", "delete_feature", "Delete")]
    current_order = ["name", "type"]
    ITEM_KEY: None | str = None  # To be defined in child classes
    SETTING_KEY: None | str = None  # Optional, only used in some child classes

    def __init__(self, disabled=False, **kwargs) -> None:
        """Each created widget needs to have a unique id, even after deletion it cannot be recycled.
        The id_counter takes care of this and feature_items dictionary keeps track of the id number and feature name.
        """
        super().__init__(disabled=disabled, **kwargs)

        self._id_counter = 0
        self.feature_items: dict = {}

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Grid(
                Button("New", variant="primary", classes="add_button"),
                Button("Rename", variant="primary", classes="rename_button"),
                Button("Duplicate", variant="primary", classes="duplicate_button"),
                Button("Delete", variant="primary", classes="delete_button"),
                # Button("Sort", variant="primary", classes="sort_button"),
                classes="buttons",
            ),
            *[
                Collapsible(title=self.ITEM_MAP[f], id="list_" + f, classes="list", collapsed=False)
                for f in self.ITEM_MAP.keys()
            ],
            id="sidebar",
        )
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

            self.feature_items[content_switcher_item_new_id] = TypeNameItem(item_type, item_name)

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
            NameInput(occupied_feature_names),
            rename_item,
        )
