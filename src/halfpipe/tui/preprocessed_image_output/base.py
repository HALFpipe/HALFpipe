# -*- coding: utf-8 -*-

from textual.widgets import (
    Label,
    ListItem,
)

from ..feature_widgets.base import FeatureItem, FeatureNameInput, FeatureSelection
from ..feature_widgets.task_based.taskbased import TaskBased
from ..utils.context import ctx


class PreprocessedOutputOptions(TaskBased):
    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        # no features for preprocessed image output!
        this_user_selection_dict["features"] = {}

    def on_mount(self) -> None:
        self.get_widget_by_id("images_to_use").border_title = "Images to use"
        self.get_widget_by_id("confounds").border_title = "Remove confounds"
        self.get_widget_by_id("preprocessing").border_title = "Preprocessing setting"
        self.get_widget_by_id("model_conditions_and_constrasts").remove()  # .styles.visibility = "hidden"

    def update_conditions_table(self):
        condition_list = []
        for value in self.get_widget_by_id("images_to_use_selection").selected:
            condition_list += self.extract_conditions(entity="task", values=[value])
        self.setting_dict["filters"][0]["values"] = self.get_widget_by_id("images_to_use_selection").selected


class PreprocessedImageOutput(FeatureSelection):
    def __init__(self, disabled=False, **kwargs) -> None:
        super().__init__(disabled=disabled, **kwargs)

    def on_mount(self) -> None:
        self.get_widget_by_id("content_switcher").border_title = "Preprocessed image output"
        self.get_widget_by_id("content_switcher").styles.border_title_color = "white"

    def action_add_feature(self) -> None:
        """Pops out the feature type selection windows and then uses add_new_feature function to mount a new feature widget."""
        occupied_feature_names = [self.feature_items[item].name for item in self.feature_items]

        def get_feature_name(value):
            # feature_type, feature_name
            self.add_new_preprocessed_image(value)

        self.app.push_screen(
            FeatureNameInput(occupied_feature_names),
            get_feature_name,
        )

    def add_new_preprocessed_image(self, feature_name: str) -> None:
        """
        In the preprocessed image output we do not use the 'feature
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
            if feature_name not in self.app.user_selections_dict:
                self.app.user_selections_dict[feature_name]["settings"]["name"] = feature_name + "Setting"
                self.app.user_selections_dict[feature_name]["settings"]["output_image"] = True

            new_content_item = PreprocessedOutputOptions(
                this_user_selection_dict=ctx.cache.user_selections_dict[feature_name],
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
