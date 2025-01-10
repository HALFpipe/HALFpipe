# -*- coding: utf-8 -*-


from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, ScrollableContainer, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, SelectionList, Static, Switch
from textual.widgets.selection_list import Selection

from ..utils.context import ctx
from ..utils.custom_switch import TextSwitch


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

    entity: str = ""
    filters: dict = {"datatype": "", "suffix": ""}
    featurefield: str = ""
    type: str = ""

    def __init__(self, this_user_selection_dict: dict, id: str | None = None, classes: str | None = None) -> None:
        """At the beginning there is a bunch of 'if not in'. If a new widget is created the pass
        this_user_selection_dict is empty and the nested keys need some initialization. On the other
        hand, if a new widget is created automatically on spec file load then this dictionary is not empty and these
        values are then used for the various widgets within this widget.
        """
        super().__init__(id=id, classes=classes)
        self.model_dict = this_user_selection_dict["models"]
        self.model_dict.setdefault("type", self.type)
        self.model_dict.setdefault("filters", [])

        # in case of loading from existing spec file or copying

        # Check if any dictionary in the list has the required key-value pairs
        def extract_from_existing_filters(filter_type_identifier):
            for filter_dict in self.model_dict["filters"]:
                if filter_type_identifier.items() <= filter_dict.items():
                    return filter_dict
            return None

        self.fd_mean_cutoff_dict = extract_from_existing_filters({"type": "cutoff", "field": "fd_mean"}) or {
            "type": "cutoff",
            "action": "exclude",
            "field": "fd_mean",
            "cutoff": "0.5",
        }

        self.fd_perc_cutoff_dict = extract_from_existing_filters({"type": "cutoff", "field": "fd_perc"}) or {
            "type": "cutoff",
            "action": "exclude",
            "field": "fd_perc",
            "cutoff": "10.0",
        }

        if self.model_dict["filters"] == []:
            self.model_dict["filters"].append(self.fd_mean_cutoff_dict)
            self.model_dict["filters"].append(self.fd_perc_cutoff_dict)

        # self.model_dict.setdefault("inputs", [])
        self.tasks_to_use: dict | None = {}
        # if images exists, i.e., bold files with task tags were correctly given
        if "inputs" not in self.model_dict:
            print("hereeeeeeeeeeeeeeeeeeeeeeeeeee 1")
            for w in ctx.cache:
                # print('wwwwwwwwwwwwwwwwwwwwwwwwwww', w)
                if "features" in ctx.cache[w] and ctx.cache[w]["features"] != {}:
                    # print('fffffffffffffffffffffffffffffff ctx.cache[w]', ctx.cache[w])
                    # print('sssssssssssssssssss ctx.cache[w][ddtype]', ctx.cache[w]['type'])
                    if ctx.cache[w]["features"]["type"] == "task_based":
                        print("heeeeeeeeeeeeeere??")
                        self.tasks_to_use[ctx.cache[w]["features"]["name"]] = True
            # print('qqqqqqqqqqqqqqqqq', self.tasks_to_use)
        else:
            print("hereeeeeeeeeeeeeeeeeeeeeeeeeee 2")
            self.tasks_to_use = {i: True for i in self.model_dict["inputs"]}

        # if self.tasks_to_use is not None:
        if "inputs" not in self.model_dict:
            self.model_dict["inputs"] = [task for task in self.tasks_to_use.keys() if self.tasks_to_use[task] is True]

        self.tasks_to_use_selection_panel = SelectionList[str](
            *[Selection(task, task, self.tasks_to_use[task]) for task in self.tasks_to_use.keys()],
            id="tasks_to_use_selection",
            classes="components",
        )

        print("qqself.fd_mean_cutoff_dictself.fd_mean_cutoff_dict", self.fd_mean_cutoff_dict)

        self.cutoff_panel = Vertical(
            Grid(
                Static("Exclude subjects based on movements", classes="description_labels"),
                TextSwitch(value=True, id="exclude_subjects"),
            ),
            Grid(
                Static("Specify the maximum allowed mean framewise displacement in mm", classes="description_labels"),
                Input(value=str(self.fd_mean_cutoff_dict["cutoff"]), placeholder="value", id="cutoff_fd_mean"),
                id="cutoff_fd_mean_panel",
            ),
            Grid(
                Static(
                    "Specify the maximum allowed percentage of frames above the framewise displacement threshold of 0.5 mm",
                    classes="description_labels",
                ),
                Input(value=str(self.fd_perc_cutoff_dict["cutoff"]), placeholder="value", id="cutoff_fd_perc"),
                id="cutoff_fd_perc_panel",
            ),
            id="cutoff_panel",
            classes="components",
        )

    async def on_mount(self) -> None:
        if self.tasks_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection").border_title = "Tasks to use"
        self.get_widget_by_id("cutoff_panel").border_title = "Cutoffs"

    @on(Input.Changed, "#cutoff_fd_mean")
    def _on_cutoff_fd_mean_input_changed(self, message: Message):
        self.fd_mean_cutoff_dict["cutoff"] = message.value

    @on(Input.Changed, "#cutoff_fd_perc")
    def _on_cutoff_fd_perc_input_changed(self, message: Message):
        self.fd_perc_cutoff_dict["cutoff"] = message.value

    @on(SelectionList.SelectedChanged, "#tasks_to_use_selection")
    def _on_selection_list_changed(self):
        # print('cccccccccccccccccccccccache', ctx.cache)
        # print('thissssssssssssss??? ',  self.get_widget_by_id("tasks_to_use_selection").selected)
        self.model_dict["inputs"] = self.get_widget_by_id("tasks_to_use_selection").selected

    @on(Switch.Changed, "#exclude_subjects")
    def on_exclude_subjects_switch_changed(self, message: Message):
        print("ssssssssssssssssssssssss", message.value)
        if message.value is True:
            self.model_dict["filters"].append(self.fd_mean_cutoff_dict)
            self.model_dict["filters"].append(self.fd_perc_cutoff_dict)
            self.get_widget_by_id("cutoff_fd_mean_panel").styles.visibility = "visible"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "visible"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.height = "auto"
        else:
            self.model_dict["filters"].remove(self.fd_mean_cutoff_dict)
            self.model_dict["filters"].remove(self.fd_perc_cutoff_dict)
            self.get_widget_by_id("cutoff_fd_mean_panel").styles.visibility = "hidden"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "hidden"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.height = 7


class InterceptOnlyModel(ModelTemplate):
    type = "me"

    def __init__(self, this_user_selection_dict=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)

        # self.default_settings["filters"] = True

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_models"):
            if self.tasks_to_use is not None:
                yield self.tasks_to_use_selection_panel
            yield self.cutoff_panel


class LinearModel(ModelTemplate):
    type = "lme"

    def __init__(self, this_user_selection_dict=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_models"):
            if self.tasks_to_use is not None:
                yield self.tasks_to_use_selection_panel
            yield self.cutoff_panel
