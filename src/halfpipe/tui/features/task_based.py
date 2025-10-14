# -*- coding: utf-8 -*-


from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.widgets import RadioButton, SelectionList, Static

from ...logging import logger
from ..general_widgets.custom_general_widgets import SwitchWithSelect
from ..general_widgets.custom_switch import TextSwitch
from ..help_functions import extract_conditions, widget_exists
from ..specialized_widgets.confirm_screen import Confirm
from ..specialized_widgets.event_file_widget import EventFilePanel
from ..standards import task_based_defaults
from ..templates.feature_template import FeatureTemplate
from .utils.model_conditions_and_contrasts import ModelConditionsAndContrasts

RadioButton.BUTTON_INNER = "X"


class TaskBased(FeatureTemplate):
    """
    Manages task-based features.

    This class extends `FeatureTemplate` to encapsulate and manage user selections
    related to task-based features,
    selecting relevant tasks, defining model conditions, and specifying
    contrasts (with integrated `ModelConditionsAndContrasts` class). In case of
    non-bids data, it uses `EventFilePanel` to handle event file selection.

    Attributes
    ----------
    entity : str
        The entity used to describe task-based features, set to "desc".
    filters : dict[str, str]
        Filters used to identify event files.
        - datatype : str
            The data type of the event files, set to "func".
        - suffix : str
            The suffix of the event files, set to "event".
    featurefield : str
        The name of the field in the features dictionary that holds the event
        file information, set to "events".
    type : str
        A string indicating the type of the feature, which is "task_based".
    file_panel_class : type[EventFilePanel]
        The class used to manage the file selection panel for event files,
        set to `EventFilePanel`.
    model_conditions_and_contrast_table : ModelConditionsAndContrasts
        The widget for managing model conditions and contrast.

    Methods
    -------
    __init__(this_user_selection_dict, id, classes)
        Initializes the TaskBased instance.
    compose() -> ComposeResult
        Composes the UI elements for the task-based feature.
    on_mount() -> None
        Performs actions when the TaskBased feature is mounted.
    mount_tasks()
        Mounts task selection and event file panels.
    _on_tasks_to_use_selection_changed(message)
        Handles changes in the task selection.
    _on_selection_list_changed_tasks_to_use_selection(message)
        Updates conditions when task selection changes.
    update_conditions_table()
        Updates the conditions table based on selected images.
    """

    entity = "desc"
    filters = {"datatype": "func", "suffix": "event"}
    featurefield = "events"
    type = "task_based"
    file_panel_class = EventFilePanel
    defaults = task_based_defaults

    def __init__(self, this_user_selection_dict, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the TaskBased instance.

        This method initializes the TaskBased object by calling the constructor
        of the parent class (`FeatureTemplate`). Moreover, it sets up the conditions
        list, and creating the `ModelConditionsAndContrasts` widget.

        Parameters
        ----------
        this_user_selection_dict : dict
            A dictionary containing the user's selection for this feature.
        id : str, optional
            The ID of the widget, by default None.
        classes : str, optional
            CSS classes for the widget, by default None.
        """

        super().__init__(this_user_selection_dict=this_user_selection_dict, defaults=self.defaults, id=id, classes=classes)
        self.feature_dict.setdefault("conditions", [])
        self.feature_dict.setdefault("model_serial_correlations", True)
        self.feature_dict.setdefault(self.featurefield, [])
        self.feature_dict.setdefault("estimation", "multiple_trial")

        self.trial_estimation_default_switch_value = False if self.feature_dict["estimation"] == "multiple_trial" else True

        self.estimation_types = {
            "single trial least squares single": "single_trial_least_squares_single",
            "single trial least squares all": "single_trial_least_squares_all",
            "multiple trial": "multiple_trial",
        }
        # Reverse mapping
        self.estimation_labels = {v: k for k, v in self.estimation_types.items()}
        self.feature_dict.setdefault("estimation", "multiple_trial")

        self.estimation_type_panel = Vertical(
            SwitchWithSelect(
                "Single trial estimation",
                options=[
                    ("least-squares all", "single_trial_least_squares_all"),
                    ("least-squares single", "single_trial_least_squares_single"),
                ],
                switch_value=self.trial_estimation_default_switch_value,
                default_option=self.feature_dict["estimation"]
                if self.feature_dict["estimation"] != "multiple_trial"
                else "single_trial_least_squares_single",
                id="estimation_type",
            ),
            id="estimation_types_selection_panel",
            classes="components",
        )

        self.estimation_type_panel.border_title = "Estimation Type"
        self.on_init = True

    def create_model_serial_correlations_panel(self):
        model_serial_correlations_panel = Horizontal(
            Static("Use auto-regressive model", classes="description_labels"),
            TextSwitch(value=self.feature_dict["model_serial_correlations"], id="model_serial_correlations_switch"),
            id="model_serial_correlations_panel",
        )
        return model_serial_correlations_panel

    @on(SwitchWithSelect.SwitchChanged, "#estimation_type")
    async def _on_estimation_type_switch_changed(self, message):
        # When selection in the estimation_types_selection widget are toggled, all selected tasks in selection
        # tasks_to_use_selection are deselected. This is to not make a mess when somebody would select first multiple_trial
        # and select some conditions and then select a different estimation and then select different tasks and then go
        # back to multiple_trial. The contrast table would then be confused, and it is safer to in such cases to start fresh.
        # Also, the contrast table is valid only for multiple_trial, so for the other ones we need to remove the contrast table
        # and also conditions key in the ctx.cache.
        # feed the dictionary (ctx.cache)
        # don't deselect when we are loading or duplicating
        if not self.on_init:
            self.get_widget_by_id("tasks_to_use_selection").deselect_all()
        else:
            self.on_init = False
        if message.switch_value:
            self.feature_dict.pop("conditions", None)
            if widget_exists(self, "model_conditions_and_constrasts"):
                await self.get_widget_by_id("model_conditions_and_constrasts").remove()
            if not widget_exists(self, "model_serial_correlations_panel"):
                await self.get_widget_by_id("estimation_types_selection_panel").mount(
                    self.create_model_serial_correlations_panel()
                )
            self.get_widget_by_id("estimation_types_selection_panel").styles.height = 8
            self.feature_dict["estimation"] = self.get_widget_by_id("estimation_type").selected
        else:
            self.feature_dict["estimation"] = "multiple_trial"
            self.feature_dict.setdefault("conditions", [])

            if not widget_exists(self, "model_conditions_and_constrasts"):
                await self.mount(
                    self.create_model_conditions_and_contrast_table(),
                    after=self.get_widget_by_id("tasks_to_use_selection_panel"),
                )
            if widget_exists(self, "model_serial_correlations_panel"):
                await self.get_widget_by_id("model_serial_correlations_panel").remove()
                self.feature_dict["model_serial_correlations"] = True
            self.get_widget_by_id("estimation_types_selection_panel").styles.height = 5

    @on(SwitchWithSelect.Changed, "#estimation_type")
    def _on_estimation_type_changed(self, message) -> None:
        """
        Handles changes in the bandpass filter type.

        This method is called when the value of the `SwitchWithSelect`
        widget with the ID "bandpass_filter_type" changes. It updates the
        bandpass filter settings in `setting_dict` based on the selected
        filter type (Gaussian or frequency-based).

        Parameters
        ----------
        message : SwitchWithSelect.Changed
            The message object containing information about the change.
        """
        estimation_type = message.value
        if message.control.switch_value is True:
            self.feature_dict["estimation"] = estimation_type
        else:
            self.feature_dict["estimation"] = "multiple_trial"

    def create_model_conditions_and_contrast_table(self):
        # We need this to get correct condition selections in the widget, to achieve this, we do the same thing as when
        # the images to use widget is updated but we accept only images that are True. The all_possible_conditions carries
        # to information of the possible choices in the condition selection widget based on the currently selected images.
        # for v in self.images_to_use["task"].keys():
        # The function itself returns a contrast table widget. We do this to get a fresh default widget each time we call
        # this function.
        if not self.images_to_use:
            raise ValueError("No images to use. 'images_to_use' cannot be empty.")

        if self.feature_dict["contrasts"] is None:
            self.feature_dict["contrasts"] = []

        all_possible_conditions = []
        for image, use in self.images_to_use["task"].items():
            if use:
                all_possible_conditions += extract_conditions(entity="task", values=[image])

        return ModelConditionsAndContrasts(
            all_possible_conditions,
            feature_contrasts_dict=self.feature_dict["contrasts"],
            feature_conditions_list=self.feature_dict["conditions"],
            id="model_conditions_and_constrasts",
            classes="components",
        )

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            yield self.estimation_type_panel
            if self.images_to_use is not None:
                yield self.tasks_to_use_selection_panel
                # mount contrast table only if estimation is set to multiple_trial, the condition with image_to_use
                # is a safety
                if self.images_to_use is not None and self.feature_dict["estimation"] == "multiple_trial":
                    yield self.create_model_conditions_and_contrast_table()
            yield self.preprocessing_panel

    async def on_mount(self) -> None:
        await self.mount_tasks()
        if self.trial_estimation_default_switch_value:
            self.estimation_type_panel.styles.height = 8
            await self.get_widget_by_id("estimation_types_selection_panel").mount(
                self.create_model_serial_correlations_panel()
            )
        else:
            self.estimation_type_panel.styles.height = 5

    async def mount_tasks(self):
        if self.images_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection_panel").border_title = "Select tasks"
        if self.app.is_bids is not True:
            await self.mount(
                EventFilePanel(
                    # default_file_tags=self.feature_dict[self.featurefield],
                    id="top_file_panel",
                    classes="components file_panel",
                ),
                after=self.get_widget_by_id("tasks_to_use_selection_panel"),
            )
            self.get_widget_by_id("top_file_panel").border_title = "Event files patterns"

    @on(SelectionList.SelectionToggled, "#tasks_to_use_selection")
    def _on_tasks_to_use_selection_changed(self, message):
        """
        Handles changes in the task selection.

        This method displays an error message if no tasks are selected
        and reselects the last selected task to ensure that at least one
        task is always selected.

        Parameters
        ----------
        message : SelectionList.SelectionToggled
            The message object containing information about the task selection change.
        """
        if len(self.get_widget_by_id(message.control.id).selected) == 0:
            self.app.push_screen(
                Confirm(
                    "You must selected at least one task!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="No images!",
                    classes="confirm_error",
                )
            )
            self.get_widget_by_id(message.control.id).select(message.selection)

    @on(file_panel_class.Changed, "#top_file_panel")
    @on(SelectionList.SelectionToggled, "#tasks_to_use_selection")
    def _on_selection_list_changed_tasks_to_use_selection(self, message):
        """
        Updates conditions when task selection changes.

        This method updates the list of possible conditions based on the
        currently selected images (`update_conditions_table`). Also, it
        provides list of all available conditions to the
        ModelConditionsAndContrasts table (`update_all_possible_conditions`).
        This is can change for examople when user load an event file. We need to know all possible conditions
        even though we are not showing them all to the user. For more see class
        `ModelConditionsAndContrasts`.

        Parameters
        ----------
        message : SelectionList.SelectionToggled | EventFilePanel.Changed
            The message object containing information about the selection change.
        """
        # this has to be split because when making a subclass, the decorator causes to ignored redefined function in the
        # subclass

        # in the old UI if the user did not select any images, the UI did not let the user proceed further. Here we do
        # more-less the same. If there are no choices user gets an error and all options are selected again.
        if widget_exists(self, "model_conditions_and_constrasts"):
            self.update_contrast_table()

    def update_contrast_table(self) -> None:
        if (
            type(self).__name__ == "TaskBased"  # and message.control.id == "tasks_to_use_selection"
        ):  # conditions are only in Task Based not in Preprocessing!
            # try to update it here? this refresh the whole condition list every time that image is changed
            all_possible_conditions = []
            if self.images_to_use is not None:
                for v in self.images_to_use["task"].keys():
                    all_possible_conditions += extract_conditions(entity="task", values=[v])
                self.get_widget_by_id("model_conditions_and_constrasts").update_all_possible_conditions(
                    all_possible_conditions
                )
                logger.debug(
                    f"UI->TaskBased._on_selection_list_changed_tasks_to_use_selection-> \
    all_possible_conditions: {all_possible_conditions}"
                )
                self.update_conditions_table()

    def update_conditions_table(self):
        """
        Updates the conditions table based on selected images.

        This method updates the condition values in the
        `ModelConditionsAndContrasts` widget to reflect the conditions
        associated with the currently selected images.
        """
        condition_list = []
        for value in self.get_widget_by_id("tasks_to_use_selection").selected:
            logger.debug(f"UI->TaskBased.update_conditions_table Extracting conditions for task: {value}")
            condition_list += extract_conditions(entity="task", values=[value])

        logger.debug(f"UI->TaskBased.update_conditions_table-> New condition list: {condition_list}")
        # force update of model_conditions_and_constrasts to reflect conditions given by the currently selected images
        self.get_widget_by_id("model_conditions_and_constrasts").condition_values = condition_list

    @on(TextSwitch.Changed, "#model_serial_correlations_switch")
    def _on_model_serial_correlations_switch_changed(self, message: Message) -> None:
        """
        Handles changes in the grand mean scaling switch.

        This method is called when the switch state of the
        `SwitchWithInputBox` widget with the ID "grand_mean_scaling"
        changes. If the switch is turned off, it sets the grand mean
        scaling value in `setting_dict` to None.

        Parameters
        ----------
        message : SwitchWithInputBox.SwitchChanged
            The message object containing information about the change.
        """
        self.feature_dict["model_serial_correlations"] = message.value
