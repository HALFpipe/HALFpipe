# -*- coding: utf-8 -*-


# from ..base import FeatureItem, FeatureNameInput, FeatureSelection
from .taskbased import TaskBased


class PreprocessedOutputOptions(TaskBased):
    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        # no features for preprocessed image output!
        this_user_selection_dict["features"] = {}

    def on_mount(self) -> None:
        print("mmmmmmmmmmmmmmmmmmmm mount subclass")
        self.get_widget_by_id("images_to_use").border_title = "Images to use"
        self.get_widget_by_id("confounds").border_title = "Remove confounds"
        self.get_widget_by_id("preprocessing").border_title = "Preprocessing setting"
        self.get_widget_by_id("model_conditions_and_constrasts").remove()  # .styles.visibility = "hidden"
        #  self.get_widget_by_id("notes").remove()
        #  self.get_widget_by_id("bandpass_filter_type").styles.visibility = "visible"
        #  self.get_widget_by_id("grand_mean_scaling").styles.visibility = "visible"

    def update_conditions_table(self):
        condition_list = []
        for value in self.get_widget_by_id("images_to_use_selection").selected:
            condition_list += self.extract_conditions(entity="task", values=[value])
        self.setting_dict["filters"][0]["values"] = self.get_widget_by_id("images_to_use_selection").selected
