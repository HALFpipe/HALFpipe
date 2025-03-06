# -*- coding: utf-8 -*-


from textual import on
from textual.containers import Grid, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, SelectionList, Static, Switch
from textual.widgets.selection_list import Selection

from ..data_analyzers.context import ctx
from ..general_widgets.custom_switch import TextSwitch


class ModelTemplate(Widget):
    """
    FeatureTemplate

    A widget for creating and managing feature-based settings and selections within a user interface. This widget
    handles both the initialization of a new widget and the loading of settings from a specification file, adapting
    its behavior accordingly.

    Attributes
    ----------
    entity : str
        An identifier for the type of entity the widget interacts with.
    filters : dict
        A dictionary specifying the datatype and suffix to filter the database queries.
    featurefield : str
        The specific feature field in the settings.
    type : str
        The type of the feature.
    file_panel_class : type
        The class used for the file panel within this widget.
    feature_dict : dict
        A dictionary containing feature-specific settings and values.
    setting_dict : dict
        A dictionary containing general settings and configuration values.
    event_file_pattern_counter : int
        A counter for file patterns.
    tagvals : list
        A list of available tags for selection.
    bandpass_filter_low_key : str
        The key for the low-pass filter setting.
    bandpass_filter_high_key : str
        The key for the high-pass filter setting.
    images_to_use : dict
        A dictionary specifying which images to use, keyed by task.
    confounds_options : dict
        Available options for confounds removal, with their descriptions and default states.
    preprocessing_panel : Vertical
        A panel containing pre-processing options such as smoothing, mean scaling, and temporal filtering.
    images_to_use_selection_panel : SelectionList
        A panel containing the selection list of images to use.
    tag_panel : SelectionList
        A panel containing the selection list of tags.

    Methods
    -------
    __init__(this_user_selection_dict, id=None, classes=None)
        Initializes the widget with user selections and settings.
    compose()
        Composes the user interface elements within the widget.
    on_file_panel_file_item_is_deleted(message)
        Handles the event when a file item is deleted from the file panel.
    on_file_panel_changed(message)
        Handles the event when the file panel changes, updating the tag selection.
    """

    type: str = ""
    bold_filedict = {"datatype": "func", "suffix": "bold"}
    aggregate_order = ["dir", "run", "ses", "task"]

    def __init__(self, this_user_selection_dict: dict, id: str | None = None, classes: str | None = None) -> None:
        """At the beginning there is a bunch of 'if not in'. If a new widget is created the pass
        this_user_selection_dict is empty and the nested keys need some initialization. On the other
        hand, if a new widget is created automatically on spec file load then this dictionary is not empty and these
        values are then used for the various widgets within this widget.
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
        ) or self.model_dict["filters"] == []:
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
            self.tasks_to_use = {task_key: task_key in self.model_dict["inputs"] for task_key in self.tasks_to_use.keys()}

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
                    value=str(next(f["cutoff"] for f in self.model_dict["filters"] if f["field"] == "fd_mean")),
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
                    value=str(next(f["cutoff"] for f in self.model_dict["filters"] if f["field"] == "fd_perc")),
                    placeholder="value",
                    id="cutoff_fd_perc",
                ),
                id="cutoff_fd_perc_panel",
            ),
            id="cutoff_panel",
            classes="components",
        )

    async def on_mount(self) -> None:
        if self.tasks_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection").border_title = "Features to use"
        self.get_widget_by_id("cutoff_panel").border_title = "Cutoffs"
        if not self.get_widget_by_id("exclude_subjects").value:
            self.hide_fd_filters()

    @on(Input.Changed, "#cutoff_fd_mean")
    def _on_cutoff_fd_mean_input_changed(self, message: Message):
        for f in self.model_dict["filters"]:
            if f.get("field") == "fd_mean":
                f["cutoff"] = message.value

    @on(Input.Changed, "#cutoff_fd_perc")
    def _on_cutoff_fd_perc_input_changed(self, message: Message):
        for f in self.model_dict["filters"]:
            if f.get("field") == "fd_perc":
                f["cutoff"] = message.value

    @on(Switch.Changed, "#exclude_subjects")
    def on_exclude_subjects_switch_changed(self, message: Message):
        if message.value is True:
            self.model_dict["filters"].extend(self.default_cutoff_filter_values)
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "visible"
            self.get_widget_by_id("cutoff_panel").styles.height = "auto"
        else:
            self.hide_fd_filters()

    def hide_fd_filters(self):
        self.model_dict["filters"] = [f for f in self.model_dict["filters"] if f["type"] != "cutoff"]
        self.get_widget_by_id("cutoff_fd_mean_panel").styles.visibility = "hidden"
        self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "hidden"
        self.get_widget_by_id("cutoff_panel").styles.height = 7
