# -*- coding: utf-8 -*-


from textual import on
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import SelectionList

from ..help_functions import extract_conditions
from ..specialized_widgets.confirm_screen import Confirm
from ..specialized_widgets.event_file_widget import EventFilePanel
from ..templates.feature_template import FeatureTemplate
from .utils.model_conditions_and_contrasts import ModelConditionsAndContrasts


class TaskBased(FeatureTemplate):
    """
    TaskBased class extends FeatureTemplate to encapsulate and manage the task-based feature operations.

    Attributes
    ----------
    entity : str
        The entity description for the task-based feature.
    filters : dict
        Additional filters applied to the feature.
    featurefield : str
        Field that encapsulates the feature data.
    type : str
        Type identifier for task-based feature.
    file_panel_class : class
        GUI panel class for handling event files.

    Methods
    -------
    compose() -> ComposeResult
        Constructs and lays out the GUI components required for task-based features.

    on_mount() -> None
        Actions to perform when the component is mounted, initializing the panel titles and managing event file panels.

    _on_selection_list_changed_tasks_to_use_selection()
        Handles updates when the image selection list changes, updating condition lists accordingly.

    update_conditions_table()
        Updates the conditions table based on the current selections, ensuring the feature and settings dictionaries are
        accurate.
    """

    entity = "desc"
    filters = {"datatype": "func", "suffix": "event"}
    featurefield = "events"
    type = "task_based"
    file_panel_class = EventFilePanel

    def __init__(self, this_user_selection_dict, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)
        if "conditions" not in self.feature_dict:
            self.feature_dict["conditions"] = []
        if self.images_to_use is not None:
            all_possible_conditions = []
            # We need this to get correct condition selections in the widget, to achieve this, we do the same thing as when
            # the images to use widget is updated but we accept only images that are True. The all_possible_conditions carries
            # to information of the possible choices in the condition selection widget based on the currently selected images.
            # for v in self.images_to_use["task"].keys():
            for image in self.images_to_use["task"]:
                if self.images_to_use["task"][image] is True:
                    all_possible_conditions += extract_conditions(entity="task", values=[image])

            if self.feature_dict["contrasts"] is not None:
                self.model_conditions_and_contrast_table = ModelConditionsAndContrasts(
                    all_possible_conditions,
                    feature_contrasts_dict=self.feature_dict["contrasts"],
                    feature_conditions_list=self.feature_dict["conditions"],
                    id="model_conditions_and_constrasts",
                    classes="components",
                )

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            if self.images_to_use is not None:
                yield self.tasks_to_use_selection_panel
                yield self.model_conditions_and_contrast_table
            yield self.preprocessing_panel

    async def on_mount(self) -> None:
        await self.mount_tasks()

    async def mount_tasks(self):
        if self.images_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection_panel").border_title = "Tasks to use"
        if self.app.is_bids is not True:
            await self.mount(
                EventFilePanel(id="top_event_file_panel", classes="file_panel components"),
                after=self.get_widget_by_id("tasks_to_use_selection_panel"),
            )
            self.get_widget_by_id("top_event_file_panel").border_title = "Event files patterns"

    @on(SelectionList.SelectionToggled, "#tasks_to_use_selection")
    def _on_tasks_to_use_selection_changed(self, message):
        if len(self.get_widget_by_id(message.control.id).selected) == 0:
            self.app.push_screen(
                Confirm(
                    "You must selected at least one image!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="No images!",
                    classes="confirm_error",
                )
            )
            self.get_widget_by_id(message.control.id).select(message.selection)


    @on(file_panel_class.Changed, "#top_event_file_panel")
    @on(SelectionList.SelectionToggled, "#tasks_to_use_selection")
    def _on_selection_list_changed_tasks_to_use_selection(self, message):
        # this has to be split because when making a subclass, the decorator causes to ignored redefined function in the
        # subclass

        # in the old UI if the user did not select any images, the UI did not let the user proceed further. Here we do
        # more-less the same. If there are no choices user gets an error and all options are selected again.


        if (
            type(self).__name__ == "TaskBased"# and message.control.id == "tasks_to_use_selection"
        ):  # conditions are only in Task Based not in Preprocessing!
            # try to update it here? this refresh the whole condition list every time that image is changed
            all_possible_conditions = []
            if self.images_to_use is not None:
                for v in self.images_to_use["task"].keys():
                    all_possible_conditions += extract_conditions(entity="task", values=[v])
                self.get_widget_by_id("model_conditions_and_constrasts").update_all_possible_conditions(
                    all_possible_conditions
                )

                self.update_conditions_table()

    def update_conditions_table(self):
        condition_list = []
        for value in self.get_widget_by_id("tasks_to_use_selection").selected:
            condition_list += extract_conditions(entity="task", values=[value])

        # force update of model_conditions_and_constrasts to reflect conditions given by the currently selected images
        self.get_widget_by_id("model_conditions_and_constrasts").condition_values = condition_list
