# -*- coding: utf-8 -*-


from textual import on
from textual.containers import Grid, Vertical
from textual.widget import Widget
from textual.widgets import Input, SelectionList, Static, Switch
from textual.widgets.selection_list import Selection

from ..data_analyzers.context import ctx
from ..general_widgets.custom_switch import TextSwitch
from ..specialized_widgets.confirm_screen import Confirm
from ..templates.feature_template import entity_label_dict

aggregate_order = ["dir", "run", "ses", "task"]


class ModelTemplate(Widget):
    """
    Base class for creating and managing group-level model settings and selections.

    This widget provides a foundation for building user interface components that
    allow users to configure and select various settings related to a specific
    group-level model. It handles the initialization of new widgets, loading settings from
    specification files, and managing model options.

    Attributes
    ----------
    type : str
        The type of the model (e.g., "group_level").
    bold_filedict : dict
        A dictionary specifying the datatype and suffix for bold files.
    aggregate_order : list[str]
        A list defining the order of aggregation entities.
    model_dict : dict
        A dictionary containing model-specific settings and values.
    is_new : bool
        A flag indicating whether a new model is being created.
    tasks_to_use : dict | None
        A dictionary specifying which tasks to use, keyed by task name.
        Values are boolean (True if selected).
    tasks_to_use_selection_panel : SelectionList
        A panel containing the selection list of tasks to use.
    cutoff_panel : Vertical
        A panel containing cutoff options for excluding subjects.
    aggregate_panel : Vertical
        A panel containing options for aggregating data.
    default_cutoff_filter_values : list[dict]
        Default values for cutoff filters.
    """

    type: str = ""
    bold_filedict = {"datatype": "func", "suffix": "bold"}
    aggregate_order = ["dir", "run", "ses", "task"]

    def __init__(self, this_user_selection_dict: dict, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the ModelTemplate widget.

        This constructor sets up the widget's internal state, including model
        settings, task selection, cutoff options, and aggregation settings. It
        handles both the creation of new models and the loading of settings
        from a specification file.

        Parameters
        ----------
        this_user_selection_dict : dict
            A dictionary containing user selections and settings. It should have
            a key "models".
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the widget, by
            default None.
        """
        super().__init__(id=id, classes=classes)
        # The variable "is_new" is a flag that signals whether we are loading (or copying) or just creating a completely
        # new model. If it is new, then in the model_dict is exactly one key, i.e., 'name'.
        self.model_dict = this_user_selection_dict["models"]
        self.is_new = list(self.model_dict.keys()) == ["name"]

        self.model_dict.setdefault("type", self.type)
        self.model_dict.setdefault("filters", [])

        # In case of loading from a file or duplicating, we check whether there are some cutoffs made, if not then we switch
        # off the cutoff widget switch. It is enough to just check one of the cutoffs in the filter field.
        if (
            self.model_dict["filters"] != [] and [f for f in self.model_dict["filters"] if f["type"] == "cutoff"] != []
        ) or self.is_new:
            cutoff_default_value = True
        else:
            cutoff_default_value = False

        if [f for f in self.model_dict["filters"] if f["type"] == "cutoff"] == []:
            self.default_cutoff_filter_values = [
                {
                    "type": "cutoff",
                    "action": "exclude",
                    "field": "fd_mean",
                    "cutoff": "0.5",
                },
                {
                    "type": "cutoff",
                    "action": "exclude",
                    "field": "fd_perc",
                    "cutoff": "10.0",
                },
            ]
            self.model_dict["filters"].extend(self.default_cutoff_filter_values)

        # First find all available tasks, assign True to all of them
        self.tasks_to_use: dict | None = {}
        for w in ctx.cache:
            if "features" in ctx.cache[w] and ctx.cache[w]["features"] != {}:
                if ctx.cache[w]["features"]["type"] != "atlas_based_connectivity":
                    self.tasks_to_use[ctx.cache[w]["features"]["name"]] = True

        # If there are no pre-existing cutoff filters, then we just assign the keys from tasks_to_use dict, otherwise
        # we change values of the keys in tasks_to_use to dict to False if there are not present in the 'inputs' dict.
        if "inputs" not in self.model_dict:
            self.model_dict["inputs"] = list(self.tasks_to_use.keys())
        else:
            for task_key in self.tasks_to_use.keys():
                for input in self.model_dict["inputs"]:
                    # There are several cases, old UI was stripping the underscore from the task name when creating aggregate
                    # model. Also, when it is just a default task name, then it will maybe not be capitalized. So, anyway,
                    # just to be sure that we loadin in all cases we try all cases.
                    for input in self.model_dict["inputs"]:
                        if task_key.replace("_", "").lower() in input.replace("_", "").lower():
                            self.tasks_to_use[task_key] = True
                            break
                    else:
                        self.tasks_to_use[task_key] = False

        self.tasks_to_use_selection_panel = SelectionList[str](
            *[Selection(task, task, self.tasks_to_use[task]) for task in self.tasks_to_use.keys()],
            id="tasks_to_use_selection",
            classes="components",
        )

        self.cutoff_panel = Vertical(
            Grid(
                Static("Exclude subjects based on movements", classes="description_labels"),
                TextSwitch(value=cutoff_default_value, id="exclude_subjects"),
            ),
            Grid(
                Static("Specify the maximum allowed mean framewise displacement in mm", classes="description_labels"),
                Input(
                    value=str(next(f["cutoff"] for f in self.model_dict["filters"] if f.get("field") == "fd_mean")),
                    placeholder="value",
                    id="cutoff_fd_mean",
                ),
                id="cutoff_fd_mean_panel",
            ),
            Grid(
                Static(
                    "Specify the maximum allowed percentage of frames above the framewise displacement threshold of 0.5 mm",
                    classes="description_labels",
                ),
                Input(
                    value=str(next(f["cutoff"] for f in self.model_dict["filters"] if f.get("field") == "fd_perc")),
                    placeholder="value",
                    id="cutoff_fd_perc",
                ),
                id="cutoff_fd_perc_panel",
            ),
            id="cutoff_panel",
            classes="components",
        )

        # Aggregation
        # Since all inputs are aggregated in the same way, we use the first one to check over what is the aggregation done.
        test_string = self.model_dict["inputs"][0]
        matches = [key for key, value in entity_label_dict.items() if value in test_string]
        self.aggregate_panel = Vertical(
            Static("Aggregate scan-level statistics before analysis", id="aggregate_switch_label", classes="label"),
            SelectionList[str](
                *[
                    Selection(entity_label_dict[entity], entity, True if entity in matches else False)
                    for entity in ctx.get_available_images.keys()
                    if entity != "sub"
                ],
                id="aggregate_selection_list",
            ),
            id="top_aggregate_panel",
            classes="components",
        )

    async def on_mount(self) -> None:
        """
        Handles actions to be taken when the component is mounted in the GUI.

        This method is called when the widget is mounted to the
        application. It sets the border titles for the selection lists and panels.
        It also hides the fd cutoff filter widgets if the cutoff switch is off.
        """
        if self.tasks_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection").border_title = "Features to use"
            self.get_widget_by_id("top_aggregate_panel").border_title = "Aggregate"

        self.get_widget_by_id("cutoff_panel").border_title = "Cutoffs"
        if not self.get_widget_by_id("exclude_subjects").value:
            self.hide_fd_filters()

    def _on_cutoff_fd_mean_input_changed(self, message: Input.Changed) -> None:
        """
        Handles changes in the fd mean cutoff input.

        This method is called when the value of the `Input` widget with the ID
        "cutoff_fd_mean" changes. It updates the `model_dict` with the new
        cutoff value for the fd mean.

        Parameters
        ----------
        message : Input.Changed
            The message object containing information about the change.
        """
        for f in self.model_dict["filters"]:
            if f.get("field") == "fd_mean":
                f["cutoff"] = message.value

    @on(Input.Changed, "#cutoff_fd_perc")
    def _on_cutoff_fd_perc_input_changed(self, message: Input.Changed) -> None:
        """
        Handles changes in the fd percentage cutoff input.

        This method is called when the value of the `Input` widget with the ID
        "cutoff_fd_perc" changes. It updates the `model_dict` with the new
        cutoff value for the fd percentage.

        Parameters
        ----------
        message : Input.Changed
            The message object containing information about the change.
        """
        for f in self.model_dict["filters"]:
            if f.get("field") == "fd_perc":
                f["cutoff"] = message.value

    @on(Switch.Changed, "#exclude_subjects")
    def on_exclude_subjects_switch_changed(self, message: Switch.Changed) -> None:
        """
        Handles changes in the exclude subjects switch.

        This method is called when the state of the `Switch` widget with the
        ID "exclude_subjects" changes. It toggles the visibility of the
        fd cutoff filter widgets and updates the `model_dict`
        accordingly.

        Parameters
        ----------
        message : Switch.Changed
            The message object containing information about the change.
        """
        if message.value is True:
            self.model_dict["filters"].extend(self.default_cutoff_filter_values)
            self.get_widget_by_id("cutoff_fd_mean_panel").styles.visibility = "visible"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "visible"
            self.get_widget_by_id("cutoff_panel").styles.height = "auto"
        else:
            self.hide_fd_filters()

    def hide_fd_filters(self):
        """
        Hides the fd cutoff filter widgets.

        This method hides the fd mean and percentage cutoff filter widgets and
        removes the corresponding filters from the `model_dict`.
        """
        self.model_dict["filters"] = [f for f in self.model_dict["filters"] if f["type"] != "cutoff"]
        self.get_widget_by_id("cutoff_fd_mean_panel").styles.visibility = "hidden"
        self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "hidden"
        self.get_widget_by_id("cutoff_panel").styles.height = 7

    @on(SelectionList.SelectionToggled, "#tasks_to_use_selection")
    def _on_tasks_to_use_selection_changed(self, message) -> None:
        """
        Handles changes in the tasks to use selection list.

        This method is called when the selection in the `SelectionList`
        widget with the ID "tasks_to_use_selection" changes. It ensures
        that at least one task is selected. If no task is selected, it
        displays an error message and reselects the previously selected task.

        Parameters
        ----------
        message : SelectionList.SelectionToggled
            The message object containing information about the change.
        """
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

    @on(SelectionList.SelectedChanged, "#tasks_to_use_selection")
    @on(SelectionList.SelectedChanged, "#aggregate_selection_list")
    def _on_aggregate__selection_or_tasks_to_use_selection_list_changed(self, message) -> None:
        """
        Handles changes in the tasks to use or aggregate selection lists.

        This method is called when the selection in either the
        `SelectionList` widget with the ID "tasks_to_use_selection" or
        "aggregate_selection_list" changes. It updates the `model_dict`
        with the selected tasks and aggregation entities. It also
        dynamically creates aggregation models and stores them in the
        context cache.

        Parameters
        ----------
        message : SelectionList.SelectedChanged
            The message object containing information about the change.
        """
        # We need to run this function also in case when the Task selection is changed because this influence also the models
        # that are aggregated and at the end which models are aggregated.
        self.model_dict["inputs"] = self.get_widget_by_id("tasks_to_use_selection").selected

        tasks_to_aggregate = self.get_widget_by_id("tasks_to_use_selection").selected
        entities_to_aggregate_over = self.get_widget_by_id("aggregate_selection_list").selected

        # Sort aggregate selection to ensure proper order
        entities_to_aggregate_over_sorted = sorted(entities_to_aggregate_over, key=lambda x: aggregate_order.index(x))

        if entities_to_aggregate_over != []:
            # aggregate_label_list = []
            models: list = []
            # We empty the input list because now all inputs are the tops of the whole aggregate hierarchy. So we append the
            # first aggregate labels to the input list of the model.
            self.model_dict["inputs"] = []
            for task_name in tasks_to_aggregate:
                aggregate_label = ""
                if entities_to_aggregate_over_sorted != []:
                    for aggregate_entity in entities_to_aggregate_over_sorted:
                        if aggregate_label == "":
                            previous_name = task_name
                            aggregate_label = (
                                "aggregate" + task_name.capitalize() + "Across" + entity_label_dict[aggregate_entity]
                            )
                        else:
                            aggregate_label = models[-1]["name"] + "Then" + entity_label_dict[aggregate_entity]
                            previous_name = models[-1]["name"]
                        models.append(
                            {
                                "name": aggregate_label,
                                "inputs": [previous_name],
                                "filters": [],
                                "type": "fe",
                                "across": aggregate_entity,
                            }
                        )
                        # Use last label for the input field
                        if aggregate_entity == entities_to_aggregate_over_sorted[-1]:
                            self.model_dict["inputs"].append(aggregate_label)

            dummy_cache_key = self.model_dict["name"] + "__aggregate_models_list"
            ctx.cache[dummy_cache_key]["models"] = {"aggregate_models_list": models}
