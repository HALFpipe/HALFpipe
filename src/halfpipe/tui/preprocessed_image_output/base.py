# -*- coding: utf-8 -*-

from textual.widgets import (
    Label,
    ListItem,
)

from ..feature_widgets.base import FeatureItem, FeatureNameInput, FeatureSelection
from ..feature_widgets.task_based.taskbased import TaskBased


class PreprocessedOutputOptions(TaskBased):
    def on_mount(self) -> None:
        self.get_widget_by_id("images_to_use").border_title = "Images to use"
        self.get_widget_by_id("confounds").border_title = "Remove confounds"
        self.get_widget_by_id("preprocessing").border_title = "Preprocessing setting"
        self.get_widget_by_id("notes").border_title = "Notes"
        self.get_widget_by_id("model_conditions_and_constrasts").styles.visibility = "hidden"
        self.get_widget_by_id("confounds").styles.offset = (0, -13)


class PreprocessedImageOutput(FeatureSelection):
    def __init__(self, app, ctx, available_images, user_selections_dict, **kwargs) -> None:
        super().__init__(
            app=app, ctx=ctx, available_images=available_images, user_selections_dict=user_selections_dict, **kwargs
        )

    def on_mount(self) -> None:
        self.get_widget_by_id("content_switcher").border_title = "Preprocessed image output"

    def action_add_feature(self) -> None:
        """Pops out the feature type selection windows and then uses add_new_feature function to mount a new feature widget."""
        occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]

        def get_feature_name(value):
            # feature_type, feature_name
            self.add_new_preprocessed_image(value)

        self.top_parent.push_screen(
            FeatureNameInput(self, occupied_feature_names),
            get_feature_name,
        )

    def add_new_preprocessed_image(self, feature_name: str) -> None:
        """Principle of adding a new feature lies in mounting a new widget while creating a new entry in the dictionary
        to keep track of the selections which are later dumped into the Context object.
        If this is a load or a duplication, then new entry is not created but read from the dictionary.
        The dictionary entry was created elsewhere.
        """
        if feature_name is not None:
            feature_type = "preprocessed_image"
            new_id = "feature_item_" + str(self._id_counter)
            self.feature_items[new_id] = FeatureItem(feature_type, feature_name)
            new_list_item = ListItem(
                Label(feature_name, id=new_id, classes="labels " + feature_type),
                id=new_id,
                classes="items",
            )
            # this dictionary will contain all made choices
            if feature_name not in self.user_selections_dict:
                self.user_selections_dict[feature_name]["features"]["name"] = feature_name
                self.user_selections_dict[feature_name]["features"]["setting"] = feature_name + "Setting"
                self.user_selections_dict[feature_name]["settings"]["name"] = feature_name + "Setting"
            new_content_item = PreprocessedOutputOptions(
                self.top_parent,
                self.ctx,
                self.available_images,
                this_user_selection_dict=self.user_selections_dict[feature_name],
                id=new_id,
                classes=feature_type,
            )
            self.get_widget_by_id("list").mount(new_list_item)
            self.get_widget_by_id("content_switcher").mount(new_content_item)
            self.get_widget_by_id("content_switcher").current = new_id
            self.get_widget_by_id("content_switcher").border_title = "{}: {}".format(
                "Preprocessed output",
                self.feature_items[new_id].name,
            )
            self.get_widget_by_id("content_switcher").styles.border_title_color = "red"
            self._id_counter += 1
