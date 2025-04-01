# -*- coding: utf-8 -*-

import copy

import inflect
from textual import on
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from ...model.tags import entity_longnames as entity_display_aliases
from ..data_analyzers.context import ctx
from ..data_analyzers.summary_steps import BoldSummaryStep
from ..data_input.base import DataSummaryLine
from ..general_widgets.custom_general_widgets import SwitchWithInputBox, SwitchWithSelect
from ..specialized_widgets.event_file_widget import FilePanelTemplate

entity_label_dict = {"dir": "Directions", "run": "Runs", "task": "Tasks", "ses": "Sessions"}

p = inflect.engine()


class FeatureTemplate(Widget):
    """
    Base class for creating and managing feature-based settings and selections.

    This widget provides a foundation for building user interface components that
    allow users to configure and select various settings related to a specific
    feature. It handles the initialization of new widgets, loading settings from
    specification files, and managing preprocessing options.

    Attributes
    ----------
    entity : str
        An identifier for the type of entity the widget interacts with (e.g., "task", "run").
    filters : dict
        A dictionary specifying the datatype and suffix to filter database queries.
        Example: `{"datatype": "func", "suffix": "bold"}`.
    featurefield : str
        The specific feature field in the settings (e.g., "atlases", "seeds").
    type : str
        The type of the feature (e.g., "atlas_based_connectivity", "reho").
    file_panel_class : type
        The class used for the file panel within this widget. Defaults to `FilePanelTemplate`.
    feature_dict : dict
        A dictionary containing feature-specific settings and values.
    setting_dict : dict
        A dictionary containing general settings and configuration values.
    event_file_pattern_counter : int
        A counter for file patterns, used when creating new file patterns.
    tagvals : list
        A list of available tags for selection.
    images_to_use : dict | None
        A dictionary specifying which images to use, keyed by entity (e.g., "task").
        Values are dictionaries mapping tag names to boolean values (True if selected).
    confounds_options : dict
        Available options for confounds removal, with their descriptions and default states.
        Keys are confound names, values are lists: `[description, default_state]`.
    preprocessing_panel : Vertical
        A panel containing pre-processing options such as smoothing, mean scaling, and temporal filtering.
    tasks_to_use_selection_panel : Vertical | None
        A panel containing the selection list of images to use.
    """

    entity: str = ""
    filters: dict = {"datatype": "", "suffix": ""}
    featurefield: str = ""
    type: str = ""
    file_panel_class = FilePanelTemplate

    def __init__(self, this_user_selection_dict: dict, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the FeatureTemplate widget.

        This constructor sets up the widget's internal state, including feature
        and general settings, preprocessing options, and image selection. It
        handles both the creation of new widgets and the loading of settings
        from a specification file.

        Note
        ----
        At the beginning there is a bunch of 'if not in'. If a new widget is created the pass
        this_user_selection_dict is empty and the nested keys need some initialization. On the other
        hand, if a new widget is created automatically on spec file load then this dictionary is not empty and these
        values are then used for the various widgets within this widget.

        Parameters
        ----------
        this_user_selection_dict : dict
            A dictionary containing user selections and settings. It should have
            keys "features" and "settings".
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the widget, by
            default None.
        """
        super().__init__(id=id, classes=classes)
        self.feature_dict = this_user_selection_dict["features"]
        self.setting_dict = this_user_selection_dict["settings"]
        self.event_file_pattern_counter = 0

        self.temp_bandpass_filter_selection: dict
        self.feature_dict.setdefault("contrasts", [])
        self.feature_dict.setdefault("type", self.type)

        self.bandpass_filter_default_switch_value = True
        if self.type in ["reho", "falff", "atlas_based_connectivity"]:
            self.setting_dict.setdefault("bandpass_filter", {"type": "frequency_based", "high": "0.1", "low": "0.01"})
        else:
            self.setting_dict.setdefault("bandpass_filter", {"type": "gaussian", "hp_width": "125", "lp_width": None})

        if self.setting_dict["bandpass_filter"]["type"] is None:
            self.bandpass_filter_default_switch_value = False

        self.setting_dict.setdefault("smoothing", {"fwhm": "6"})

        self.grand_mean_scaling_default_switch_value = True
        self.setting_dict.setdefault("grand_mean_scaling", {"mean": 10000})
        if self.setting_dict["grand_mean_scaling"]["mean"] is None:
            self.grand_mean_scaling_default_switch_value = False

        self.setting_dict.setdefault(
            "filters",
            [
                {"type": "tag", "action": "include", "entity": entity, "values": []}
                for entity, tags in ctx.get_available_images.items()
                if entity == "task"
            ],
        )

        self.images_to_use: dict | None
        # if images exists, i.e., bold files with task tags were correctly given
        if ctx.get_available_images != {}:
            # In "Features" we use only "Tasks" !
            # loop around available tasks to create a selection dictionary for the selection widget
            # if empty setting_dict["filters"] (meaning to loading or duplicating is happening) assign True to all images
            # Case 1) filters is an empty list. Meaning: we are loading from a file and there are no filters so we assign
            # all values as True
            if self.setting_dict["filters"] == []:
                # self.images_to_use = {"task": {task: True for task in ctx.get_available_images["task"]}}
                self.images_to_use = {
                    entity: {tag: True for tag in tags}
                    for entity, tags in ctx.get_available_images.items()
                    if entity == "task"
                }
            # Case 2) filters is not an empty list but the values are empty. Meaning: there are two possibilities. Either this
            # is fresh new feature or we are making a duplicate from a feature that we
            # previously have created. We assign all values to False
            else:
                self.images_to_use = {
                    entity: {tag: False for tag in tags}
                    for entity, tags in ctx.get_available_images.items()
                    if entity == "task"
                }
                # Case 3) We are loading or duplicating and some tasks are on and some are off. This means some filters are on
                # and some off. Based on what is present in the filters dictionary under values, we assign True.
                if self.setting_dict["filters"][0]["values"] != []:
                    for image in self.setting_dict["filters"][0]["values"]:
                        self.images_to_use["task"][image] = True
        else:
            self.images_to_use = None

        confounds_options = {
            "ICA-AROMA": ["ICA-AROMA", False],
            "(trans|rot)_[xyz]": ["Motion parameters", False],
            "(trans|rot)_[xyz]_derivative1": ["Derivatives of motion parameters", False],
            "(trans|rot)_[xyz]_power2": ["Motion parameters squared", False],
            "(trans|rot)_[xyz]_derivative1_power2": ["Derivatives of motion parameters squared", False],
            "motion_outlier[0-9]+": ["Motion scrubbing", False],
            "a_comp_cor_0[0-4]": ["aCompCor (top five components)", False],
            "white_matter": ["White matter signal", False],
            "csf": ["CSF signal", False],
            "global_signal": ["Global signal", False],
        }

        for confound in self.setting_dict.get("confounds_removal", []):
            confounds_options[confound][1] = True

        self.confounds_options = confounds_options
        self.create_preprocessing_panel(self.setting_dict["smoothing"]["fwhm"])

        if self.images_to_use is not None:
            self.tasks_to_use_selection_panel = Vertical(
                SelectionList[str](
                    *[Selection(image, image, self.images_to_use["task"][image]) for image in self.images_to_use["task"]],
                    id="tasks_to_use_selection",
                ),
                DataSummaryLine(id="feedback_task_filtered_bold"),
                id="tasks_to_use_selection_panel",
                classes="components",
            )

    def create_preprocessing_panel(self, default_smoothing_value):
        """
        Creates the preprocessing panel with the given default smoothing value.

        This method constructs the preprocessing panel, which includes options
        for smoothing, grand mean scaling, and temporal filtering. The panel is
        created dynamically to accommodate different smoothing settings (e.g.,
        smoothing in settings vs. smoothing in features).

        Parameters
        ----------
        default_smoothing_value : Any
            The default smoothing value (FWHM in mm).
        """
        # We need to create preprocessing panel via a separate function because from reho and falff the smoothing is in
        # features not in settings. Hence to override the default value when we for example load from a spec file, we need
        # to refresh the preprocessing panel after we switch from smoothing in settings to smoothing in features. For more
        # look for example at init at the reho.py
        if default_smoothing_value is None:
            smoothing_default_switch_value = False
        else:
            smoothing_default_switch_value = True
        # update low and high pass filter is done automatically at start, the SwitchWithSelect.Changed
        # "#bandpass_filter_type") automatically triggers def _on_bandpass_filter_type_change
        self.preprocessing_panel = Vertical(
            SwitchWithInputBox(
                label="Smoothing (FWHM in mm)",
                value=str(default_smoothing_value) if default_smoothing_value is not None else default_smoothing_value,
                switch_value=smoothing_default_switch_value,
                classes="switch_with_input_box",
                id="smoothing",
            ),
            SwitchWithInputBox(
                label="Grand mean scaling",
                value=str(self.setting_dict["grand_mean_scaling"]["mean"])
                if self.setting_dict["grand_mean_scaling"]["mean"] is not None
                else self.setting_dict["grand_mean_scaling"]["mean"],
                switch_value=self.grand_mean_scaling_default_switch_value,
                classes="switch_with_input_box additional_preprocessing_settings",
                id="grand_mean_scaling",
            ),
            SwitchWithSelect(
                "Temporal filter",
                options=[("Gaussian-weighted", "gaussian"), ("Frequency-based", "frequency_based")],
                switch_value=self.bandpass_filter_default_switch_value,
                default_option=self.setting_dict["bandpass_filter"]["type"],
                id="bandpass_filter_type",
                classes="additional_preprocessing_settings",
            ),
            SwitchWithInputBox(
                label="Low-pass temporal filter width \n(in seconds)",
                value=None,
                classes="switch_with_input_box bandpass_filter_values",
                id="bandpass_filter_lp_width",
            ),
            SwitchWithInputBox(
                label="High-pass temporal filter width \n(in seconds)",
                value=None,
                classes="switch_with_input_box bandpass_filter_values",
                id="bandpass_filter_hp_width",
            ),
            SelectionList[str](
                *[
                    Selection(self.confounds_options[key][0], key, self.confounds_options[key][1])
                    for key in self.confounds_options
                ],
                #       classes="components",
                id="confounds_selection",
            ),
            id="preprocessing",
            classes="components",
        )

    async def on_mount(self) -> None:
        """
        Handles actions to be taken when the component is mounted in the UI.

        This method is called when the widget is mounted to the
        application. It sets the border titles for the input box, tag
        selection list, and file panel.
        """
        if self.images_to_use is not None:
            # Since there are now always only 'Tasks' in Features, we can name the panel 'Tasks to use', instead of
            # 'Images to Use'
            self.get_widget_by_id("tasks_to_use_selection_panel").border_title = "Select tasks"
        self.get_widget_by_id("confounds_selection").border_title = "Remove confounds"
        self.get_widget_by_id("preprocessing").border_title = "Preprocessing settings"
        if self.get_widget_by_id("bandpass_filter_type").switch_value is False:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_lp_width").switch_value = False
            self.get_widget_by_id("bandpass_filter_hp_width").switch_value = False
        self.update_dataline()

    @on(SelectionList.SelectedChanged, "#tasks_to_use_selection")
    def _on_selection_list_changed(self, message) -> None:
        """
        Handles changes in the selection list of tasks to use.

        This method is called when the selection in the `SelectionList`
        widget with the ID "tasks_to_use_selection" changes. It updates
        the filters in `setting_dict` based on the selected tasks.

        Parameters
        ----------
        message : SelectionList.SelectedChanged
            The message object containing information about the change.
        """
        # Since now we are using only tasks, the loop might not be neccessery, because there is now only one selection and that
        # is the 'task'. Before there were also sessions, dirs, runs. The  message.control.id[:-18] extracts the string 'task'
        # from 'tasks_to_use_selection' to match the particular entry in the filters.
        for f in self.setting_dict["filters"]:
            if f["entity"] == message.control.id[:-18]:
                f["values"] = self.get_widget_by_id(message.control.id).selected
        self.update_dataline()

    def update_dataline(self) -> None:
        """
        Updates the data line with the current selection.

        This method updates the data line with the current selection of
        tasks and other settings.
        """
        bold_summary_step = BoldSummaryStep()
        bold_summary = bold_summary_step.get_summary
        bold_summary_task_filtered = {}
        filepaths = ctx.database.applyfilters(set(bold_summary["files"]), self.setting_dict.get("filters"))
        bold_summary_task_filtered["files"] = filepaths
        n_by_tag = bold_summary["n_by_tag"]
        number_of_currently_selected_tasks = self.get_widget_by_id("tasks_to_use_selection").selected

        if isinstance(n_by_tag, dict):  # Ensure n_by_tag is a dictionary
            for tag in n_by_tag.keys():
                if tag == "task":
                    n_by_tag[tag] = len(number_of_currently_selected_tasks)

            tagmessages = [
                p.inflect(f"{n} plural('{entity_display_aliases.get(tagname, tagname)}', {n})")
                for tagname, n in n_by_tag.items()
                if n > 0
            ]
            filetype = "BOLD image"
            message = p.inflect(f"Found {len(filepaths)} {filetype} plural('file', {len(filepaths)})")
            message += " "
            message += "for"
            message += " "
            message += p.join(tagmessages)

            bold_summary_task_filtered["message"] = message

            self.get_widget_by_id("feedback_task_filtered_bold").update_summary(bold_summary_task_filtered)
        else:
            raise Exception("Something went wrong, n_by_tag is not a dictionary!")

    @on(SwitchWithSelect.SwitchChanged, "#bandpass_filter_type")
    def _on_bandpass_filter_type_switch_changed(self, message):
        """
        Handles changes in the bandpass filter type switch.

        This method is called when the switch state of the
        `SwitchWithSelect` widget with the ID "bandpass_filter_type"
        changes. It toggles the visibility of the low-pass and high-pass
        filter widgets and updates the `setting_dict` accordingly.

        Parameters
        ----------
        message : SwitchWithSelect.SwitchChanged
            The message object containing information about the change.
        """
        # This serves for on/off of the bandpass filter. When Off, we need to hide some widgets, the opposite when On.
        # There is a special case when filter was Off and the feature was duplicated, then after turning it on we need to pass
        # some default values to the lp and hp widgets.
        if message.switch_value is True:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "visible"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "visible"
            self.get_widget_by_id("bandpass_filter_lp_width").get_widget_by_id(
                "input_switch_input_box"
            ).styles.visibility = "visible"
            self.get_widget_by_id("bandpass_filter_hp_width").get_widget_by_id(
                "input_switch_input_box"
            ).styles.visibility = "visible"
            self.get_widget_by_id("preprocessing").styles.height = 32
            self.get_widget_by_id("confounds_selection").styles.offset = (0, 1)
            self.setting_dict["bandpass_filter"] = self.temp_bandpass_filter_selection
            # pass some default values to lp and hp widgets using this function
            self.set_bandpass_filter_values_after_toggle(message.control.value)
        else:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "hidden"
            # The visibility of the input box of SwitchWithInputBox widget is on mount set by presence of string,
            # since a string can be passed as a default value, we need to also override the input_switch_input_box subwidget
            # of the SwitchWithInputBox widget
            self.get_widget_by_id("bandpass_filter_lp_width").get_widget_by_id(
                "input_switch_input_box"
            ).styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_hp_width").get_widget_by_id(
                "input_switch_input_box"
            ).styles.visibility = "hidden"
            self.get_widget_by_id("preprocessing").styles.height = 26
            self.get_widget_by_id("confounds_selection").styles.offset = (0, -5)
            self.temp_bandpass_filter_selection = copy.deepcopy(self.setting_dict["bandpass_filter"])
            self.setting_dict["bandpass_filter"]["type"] = None

    @on(SwitchWithSelect.Changed, "#bandpass_filter_type")
    def _on_bandpass_filter_type_changed(self, message) -> None:
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
        bandpass_filter_type = message.value
        if message.control.switch_value is True:
            self.set_bandpass_filter_values_after_toggle(bandpass_filter_type)

    def set_bandpass_filter_values_after_toggle(self, bandpass_filter_type) -> None:
        """
        Sets the bandpass filter values after toggling the filter type.

        This method is called after the bandpass filter type is toggled.
        It updates the labels and values of the low-pass and high-pass
        filter widgets based on the selected filter type. It also updates
        the `setting_dict` with the new filter values.

        Parameters
        ----------
        bandpass_filter_type : str
            The selected bandpass filter type ("gaussian" or
            "frequency_based").
        """
        if bandpass_filter_type == "frequency_based":
            lowest_value = (
                self.setting_dict["bandpass_filter"]["low"]
                if "low" in self.setting_dict["bandpass_filter"] and self.setting_dict["bandpass_filter"]["low"] is None
                else str(self.setting_dict["bandpass_filter"]["low"])
                if "low" in self.setting_dict["bandpass_filter"]
                else "0.01"
            )
            highest_value = (
                self.setting_dict["bandpass_filter"]["high"]
                if "high" in self.setting_dict["bandpass_filter"] and self.setting_dict["bandpass_filter"]["high"] is None
                else str(self.setting_dict["bandpass_filter"]["high"])
                if "high" in self.setting_dict["bandpass_filter"]
                else "0.1"
            )

            self.get_widget_by_id("bandpass_filter_lp_width").update_label("Low-pass temporal filter width \n(in Hertz)")
            self.get_widget_by_id("bandpass_filter_hp_width").update_label("High-pass temporal filter width \n(in Hertz)")
            # set defaults on toggle
            self.get_widget_by_id("bandpass_filter_lp_width").update_value(lowest_value if lowest_value is not None else "")
            self.get_widget_by_id("bandpass_filter_lp_width").update_switch_value(lowest_value is not None)
            self.get_widget_by_id("bandpass_filter_hp_width").update_value(highest_value if highest_value is not None else "")
            self.get_widget_by_id("bandpass_filter_lp_width").update_switch_value(highest_value is not None)
            self.setting_dict["bandpass_filter"]["low"] = lowest_value
            self.setting_dict["bandpass_filter"]["high"] = highest_value
            self.setting_dict["bandpass_filter"].pop("lp_width", None)
            self.setting_dict["bandpass_filter"].pop("hp_width", None)
        elif bandpass_filter_type == "gaussian":
            lowest_value = (
                self.setting_dict["bandpass_filter"]["lp_width"]
                if "lp_width" in self.setting_dict["bandpass_filter"]
                and self.setting_dict["bandpass_filter"]["lp_width"] is None
                else str(self.setting_dict["bandpass_filter"]["lp_width"])
                if "lp_width" in self.setting_dict["bandpass_filter"]
                else "0.01"
            )
            highest_value = (
                self.setting_dict["bandpass_filter"]["hp_width"]
                if "hp_width" in self.setting_dict["bandpass_filter"]
                and self.setting_dict["bandpass_filter"]["hp_width"] is None
                else str(self.setting_dict["bandpass_filter"]["hp_width"])
                if "hp_width" in self.setting_dict["bandpass_filter"]
                else "125"
            )

            self.get_widget_by_id("bandpass_filter_lp_width").update_label("Low-pass temporal filter width \n(in seconds)")
            self.get_widget_by_id("bandpass_filter_hp_width").update_label("High-pass temporal filter width \n(in seconds)")
            # set defaults on toggle
            self.get_widget_by_id("bandpass_filter_lp_width").update_value(lowest_value if lowest_value is not None else "")
            self.get_widget_by_id("bandpass_filter_lp_width").update_switch_value(lowest_value is not None)
            self.get_widget_by_id("bandpass_filter_hp_width").update_value(highest_value if highest_value is not None else "")
            self.get_widget_by_id("bandpass_filter_hp_width").update_switch_value(highest_value is not None)
            # on mount the app also runs through this part and since 'frequency_based' was never set, the low and high
            # do not exist
            if "low" in self.setting_dict["bandpass_filter"]:
                self.setting_dict["bandpass_filter"]["lp_width"] = lowest_value
                self.setting_dict["bandpass_filter"]["hp_width"] = highest_value
                # self.setting_dict["bandpass_filter"]["lp_width"] = self.setting_dict["bandpass_filter"]["low"]
                # self.setting_dict["bandpass_filter"]["hp_width"] = self.setting_dict["bandpass_filter"]["high"]
                self.setting_dict["bandpass_filter"].pop("low", None)
                self.setting_dict["bandpass_filter"].pop("high", None)

        self.setting_dict["bandpass_filter"]["type"] = bandpass_filter_type

    @on(SwitchWithInputBox.Changed, "#grand_mean_scaling")
    def _on_grand_mean_scaling_changed(self, message: Message) -> None:
        """
        Handles changes in the grand mean scaling value.

        This method is called when the value of the `SwitchWithInputBox`
        widget with the ID "grand_mean_scaling" changes. It updates the
        `setting_dict` with the new grand mean scaling value.

        Parameters
        ----------
        message : SwitchWithInputBox.Changed
            The message object containing information about the change.
        """
        self.setting_dict["grand_mean_scaling"]["mean"] = message.value if message.value != "" else None

    @on(SwitchWithInputBox.SwitchChanged, "#grand_mean_scaling")
    def _on_grand_mean_scaling_switch_changed(self, message: Message) -> None:
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
        if message.switch_value is False:
            self.setting_dict["grand_mean_scaling"]["mean"] = None

    @on(SwitchWithInputBox.Changed, ".bandpass_filter_values")
    def _on_bandpass_filter_xp_width_changed(self, message: Message) -> None:
        """
        Handles changes in the bandpass filter width.

        This method is called when the value of a `SwitchWithInputBox`
        widget with the class "bandpass_filter_values" changes. It
        updates the corresponding bandpass filter setting in
        `setting_dict` based on the widget's ID.

        Parameters
        ----------
        message : SwitchWithInputBox.Changed
            The message object containing information about the change.
        """
        the_id = message.control.id.replace("bandpass_filter_", "")
        if self.setting_dict["bandpass_filter"]["type"] == "frequency_based":
            mapping = {"lp_width": "low", "hp_width": "high"}
            the_id = mapping.get(the_id)
        if message.control.switch_value is True:
            self.setting_dict["bandpass_filter"][the_id] = message.value if message.value != "" else None

    @on(SwitchWithInputBox.Changed, "#smoothing")
    def _on_smoothing_changed(self, message: Message) -> None:
        """
        Handles changes in the smoothing value.

        This method is called when the value of the `SwitchWithInputBox`
        widget with the ID "smoothing" changes. It updates the smoothing
        value in `setting_dict`.

        Parameters
        ----------
        message : SwitchWithInputBox.Changed
            The message object containing information about the change.
        """
        # the function needs to be separated so that we can override it in reho and falff subclasses
        self.set_smoothing_value(message.value)

    def set_smoothing_value(self, value):
        """
        Sets the smoothing value.

        This method sets the smoothing value in the `setting_dict`.

        Parameters
        ----------
        value : str | None
            The new smoothing value.
        """
        self.setting_dict["smoothing"]["fwhm"] = value if value != "" else None

    @on(SwitchWithInputBox.SwitchChanged, "#smoothing")
    def _on_smoothing_switch_changed(self, message: Message) -> None:
        """
        Handles changes in the smoothing switch.

        This method is called when the switch state of the
        `SwitchWithInputBox` widget with the ID "smoothing" changes. It
        updates the smoothing settings in `setting_dict` based on the
        switch state.

        Parameters
        ----------
        message : SwitchWithInputBox.SwitchChanged
            The message object containing information about the change.
        """
        # the function needs to be separated so that we can override it in reho and falff subclasses
        self.set_smoothing_switch_value(message.switch_value)

    def set_smoothing_switch_value(self, switch_value) -> None:
        """
        Sets the smoothing switch value.

        This method sets the smoothing switch value in the `setting_dict`.

        Parameters
        ----------
        switch_value : bool
            The new smoothing switch value.
        """
        # in ReHo the smoothing is in features
        if switch_value is True:
            self.setting_dict["smoothing"] = {"fwhm": "6"}
        elif switch_value is False:
            self.setting_dict["smoothing"]["fwhm"] = None

    @on(SelectionList.SelectedChanged, "#confounds_selection")
    def feed_feature_dict_confounds(self) -> None:
        """
        Feeds the feature dictionary with confounds.

        This method is called when the selection in the `SelectionList`
        widget with the ID "confounds_selection" changes. It updates the
        `setting_dict` with the selected confounds.
        """
        confounds = self.get_widget_by_id("confounds_selection").selected.copy()
        # "ICA-AROMA" is in a separate field, so here this is taken care of
        if "ICA-AROMA" in self.get_widget_by_id("confounds_selection").selected:
            confounds.remove("ICA-AROMA")
            self.setting_dict["ica_aroma"] = True
        else:
            self.setting_dict["ica_aroma"] = False

        self.setting_dict["confounds_removal"] = confounds
