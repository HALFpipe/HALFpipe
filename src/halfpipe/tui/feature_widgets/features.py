# -*- coding: utf-8 -*-
# ok to review

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.custom_general_widgets import LabelWithInputBox, SwitchWithInputBox, SwitchWithSelect
from ..utils.event_file_widget import AtlasFilePanel, EventFilePanel, FilePanelTemplate, SeedMapFilePanel, SpatialMapFilePanel
from ..utils.utils import extract_conditions, extract_name_part
from .model_conditions_and_contrasts import ModelConditionsAndContrasts


class FeatureTemplate(Widget):
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
    file_panel_class = FilePanelTemplate

    def __init__(self, this_user_selection_dict: dict, id: str | None = None, classes: str | None = None) -> None:
        """At the beginning there is a bunch of 'if not in'. If a new widget is created the pass
        this_user_selection_dict is empty and the nested keys need some initialization. On the other
        hand, if a new widget is created automatically on spec file load then this dictionary is not empty and these
        values are then used for the various widgets within this widget.
        """
        super().__init__(id=id, classes=classes)
        self.feature_dict = this_user_selection_dict["features"]
        self.setting_dict = this_user_selection_dict["settings"]
        self.event_file_pattern_counter = 0
        filepaths = ctx.database.get(**self.filters)
        self.tagvals = ctx.database.tagvalset(self.entity, filepaths=filepaths)

        # Keys to check
        # TODO The whole tagvals logic is not good, it needs some improvements.
        tag_keys = ["seeds", "atlases", "maps"]
        existing_tag = next((tag for tag in tag_keys if tag in self.feature_dict), None)
        if existing_tag is not None:
            self.tagvals = set(self.feature_dict[existing_tag])
        if self.tagvals is None:
            self.tagvals = []

        if "contrasts" not in self.feature_dict:
            self.feature_dict["contrasts"] = []
        if "type" not in self.feature_dict:
            self.feature_dict["type"] = self.type
        # These two are here for the case of atlases
        if "min_region_coverage" not in self.feature_dict:
            self.feature_dict["min_region_coverage"] = 0.8
        if self.featurefield not in self.feature_dict:
            self.feature_dict[self.featurefield] = []

        self.bandpass_filter_low_key = "lp_width"
        self.bandpass_filter_high_key = "hp_width"
        if "bandpass_filter" not in self.setting_dict:
            self.setting_dict["bandpass_filter"] = {"type": "gaussian", "hp_width": 125, "lp_width": None}
        else:
            # if we are working with existing dict (i.e. loading from a spec file), then we must identify whether it is
            # gaussian or frequency based filter, so that we can set the correct keys
            if self.setting_dict["bandpass_filter"]["type"] == "frequency_based":
                self.bandpass_filter_low_key = "low"
                self.bandpass_filter_high_key = "high"

        if "smoothing" not in self.setting_dict:
            self.setting_dict["smoothing"] = {"fwhm": 0}

        if "filters" not in self.setting_dict:
            self.setting_dict["filters"] = [{"type": "tag", "action": "include", "entity": "task", "values": []}]
        if "grand_mean_scaling" not in self.setting_dict:
            self.setting_dict["grand_mean_scaling"] = {"mean": 10000.0}
        self.images_to_use: dict | None
        if ctx.get_available_images != {}:
            self.images_to_use = {"task": {task: True for task in ctx.get_available_images["task"]}}
        else:
            self.images_to_use = None

        if self.images_to_use is not None:
            if self.setting_dict["filters"] != []:
                for image in self.setting_dict["filters"][0]["values"]:
                    self.images_to_use["task"][image] = True
            else:
                for image in self.images_to_use["task"]:
                    self.images_to_use["task"][image] = True

        confounds_options = {
            "ICA-AROMA": ["ICA-AROMA", False],
            "(trans|rot)_[xyz]": ["Motion parameters", False],
            "(trans|rot)_[xyz]_derivative1": ["Derivatives of motion parameters", False],
            "(trans|rot)_[xyz]_power2": ["Motion parameters squared", False],
            "(trans|rot)_[xyz]_derivative1_power2": ["Derivatives of motion parameters squared", False],
            "a_comp_cor_0[0-4]": ["aCompCor (top five components)", False],
            "white_matter": ["White matter signal", False],
            "csf": ["CSF signal", False],
            "global_signal": ["Global signal", False],
        }

        if "confounds_removal" in self.setting_dict:
            for confound in self.setting_dict["confounds_removal"]:
                confounds_options[confound][1] = True

        # if self.feature_dict["contrasts"] is not None:
        #     self.model_conditions_and_contrast_table = ModelConditionsAndContrasts(
        #         all_possible_conditions,
        #         feature_contrasts_dict=self.feature_dict["contrasts"],
        #         id="model_conditions_and_constrasts",
        #         classes="components",
        #     )
        self.confounds_options = confounds_options
        self.preprocessing_panel = Vertical(
            SwitchWithInputBox(
                label="Smoothing (FWHM in mm)",
                value=self.setting_dict["smoothing"]["fwhm"],
                classes="switch_with_input_box",
                id="smoothing",
            ),
            SwitchWithInputBox(
                label="Grand mean scaling",
                value=self.setting_dict["grand_mean_scaling"]["mean"],
                classes="switch_with_input_box additional_preprocessing_settings",
                id="grand_mean_scaling",
            ),
            SwitchWithSelect(
                "Temporal filter",
                options=[("Gaussian-weighted", "gaussian"), ("Frequency-based", "frequency_based")],
                switch_value=True,
                id="bandpass_filter_type",
                classes="additional_preprocessing_settings",
            ),
            SwitchWithInputBox(
                label="Low-pass temporal filter width \n(in seconds)",
                value=self.setting_dict["bandpass_filter"][self.bandpass_filter_low_key],
                switch_value=False,
                classes="switch_with_input_box bandpass_filter_values",
                id="bandpass_filter_lp_width",
            ),
            SwitchWithInputBox(
                label="High-pass temporal filter width \n(in seconds)",
                value=self.setting_dict["bandpass_filter"][self.bandpass_filter_high_key],
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

        if self.images_to_use is not None:
            self.images_to_use_selection_panel = SelectionList[str](
                *[Selection(image, image, self.images_to_use["task"][image]) for image in self.images_to_use["task"].keys()],
                id="images_to_use_selection",
                classes="components",
            )
        self.tag_panel = SelectionList[str](
            *[Selection(tag, tag, True) for tag in self.tagvals], id="tag_selection", classes="components"
        )

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            if self.images_to_use is not None:
                yield self.images_to_use_selection_panel
            yield self.file_panel_class(id="top_file_panel", classes="components file_panel")
            yield LabelWithInputBox(
                label="Minimum atlas region coverage by individual brain mask",
                value=self.feature_dict["min_region_coverage"],
                classes="switch_with_input_box components",
                id="minimum_coverage",
            )
            yield self.preprocessing_panel

    @on(file_panel_class.FileItemIsDeleted, "#top_file_panel")
    def on_file_panel_file_item_is_deleted(self, message: Message):
        self.update_tag_selection_by_children_walk(set([]))

    async def on_mount(self) -> None:
        if self.images_to_use is not None:
            self.get_widget_by_id("images_to_use_selection").border_title = "Images to use"
        self.get_widget_by_id("confounds_selection").border_title = "Remove confounds"
        self.get_widget_by_id("preprocessing").border_title = "Preprocessing setting"
        if self.get_widget_by_id("bandpass_filter_type").switch_value is False:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "hidden"

    # @on(SelectionList.SelectedChanged, "#tag_selection")
    # def on_tag_selection_changed(self, selection_list):
    #     self.feature_dict[self.featurefield] = selection_list.control.selected

    @on(SwitchWithSelect.SwitchChanged, "#bandpass_filter_type")
    def _on_bandpass_filter_type_switch_changed(self, message):
        if message.switch_value is True:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "visible"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "visible"
            self.get_widget_by_id("preprocessing").styles.height = 32
            self.get_widget_by_id("confounds_selection").styles.offset = (0, 1)
        else:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "hidden"
            self.get_widget_by_id("preprocessing").styles.height = 26
            self.get_widget_by_id("confounds_selection").styles.offset = (0, -5)

    @on(SwitchWithSelect.Changed, "#bandpass_filter_type")
    def _on_bandpass_filter_type_changed(self, message):
        if message.value == "frequency_based":
            self.get_widget_by_id("bandpass_filter_lp_width").update_label("Low-pass temporal filter width \n(in Hertz)")
            self.get_widget_by_id("bandpass_filter_hp_width").update_label("High-pass temporal filter width \n(in Hertz)")
            # set defaults on toggle
            self.get_widget_by_id("bandpass_filter_lp_width").update_value("0.01")
            self.get_widget_by_id("bandpass_filter_lp_width").update_switch_value(True)
            self.get_widget_by_id("bandpass_filter_hp_width").update_value("0.1")
            self.setting_dict["bandpass_filter"]["low"] = "0.01"
            self.setting_dict["bandpass_filter"]["high"] = "0.1"
            # self.setting_dict["bandpass_filter"]["low"] = self.setting_dict["bandpass_filter"]["lp_width"]
            # self.setting_dict["bandpass_filter"]["high"] = self.setting_dict["bandpass_filter"]["hp_width"]
            self.setting_dict["bandpass_filter"].pop("lp_width")
            self.setting_dict["bandpass_filter"].pop("hp_width")
        elif message.value == "gaussian":
            self.get_widget_by_id("bandpass_filter_lp_width").update_label("Low-pass temporal filter width \n(in seconds)")
            self.get_widget_by_id("bandpass_filter_hp_width").update_label("High-pass temporal filter width \n(in seconds)")
            # set defaults on toggle
            self.get_widget_by_id("bandpass_filter_lp_width").update_value(None)
            self.get_widget_by_id("bandpass_filter_lp_width").update_switch_value(False)
            self.get_widget_by_id("bandpass_filter_hp_width").update_value("125")
            # on mount the app also runs through this part and since 'frequency_based' was never set, the low and high
            # do not exist
            if "low" in self.setting_dict["bandpass_filter"]:
                self.setting_dict["bandpass_filter"]["lp_width"] = None
                self.setting_dict["bandpass_filter"]["hp_width"] = "125"
                # self.setting_dict["bandpass_filter"]["lp_width"] = self.setting_dict["bandpass_filter"]["low"]
                # self.setting_dict["bandpass_filter"]["hp_width"] = self.setting_dict["bandpass_filter"]["high"]
                self.setting_dict["bandpass_filter"].pop("low")
                self.setting_dict["bandpass_filter"].pop("high")

        self.setting_dict["bandpass_filter"]["type"] = message.value

    @on(LabelWithInputBox.Changed, "#minimum_coverage")
    def _on_label_with_input_box_changed(self, message: Message):
        self.feature_dict["min_region_coverage"] = message.value

    @on(SwitchWithInputBox.Changed, "#grand_mean_scaling")
    def _on_grand_mean_scaling_changed(self, message: Message):
        self.setting_dict["grand_mean_scaling"]["mean"] = message.value

    @on(SwitchWithInputBox.Changed, ".bandpass_filter_values")
    def _on_bandpass_filter_xp_width_changed(self, message: Message):
        the_id = message.control.id.replace("bandpass_filter_", "")
        if self.setting_dict["bandpass_filter"]["type"] == "frequency_based":
            mapping = {"lp_width": "low", "hp_width": "high"}
            the_id = mapping.get(the_id)
        self.setting_dict["bandpass_filter"][the_id] = message.value

    @on(SwitchWithInputBox.Changed, "#smoothing")
    def _on_smoothing_changed(self, message: Message):
        if "smoothing" in self.setting_dict:
            self.setting_dict["smoothing"]["fwhm"] = message.value
        elif "smoothing" in self.feature_dict:
            self.feature_dict["smoothing"]["fwhm"] = message.value

    @on(SelectionList.SelectedChanged, "#images_to_use_selection")
    def _on_selection_list_changed(self):
        self.setting_dict["filters"][0]["values"] = self.get_widget_by_id("images_to_use_selection").selected

    @on(SelectionList.SelectedChanged, "#confounds_selection")
    def feed_feature_dict_confounds(self):
        confounds = self.get_widget_by_id("confounds_selection").selected.copy()
        # "ICA-AROMA" is in a separate field, so here this is taken care of
        if "ICA-AROMA" in self.get_widget_by_id("confounds_selection").selected:
            confounds.remove("ICA-AROMA")
            self.setting_dict["ica_aroma"] = True
        else:
            self.setting_dict["ica_aroma"] = False

        self.setting_dict["confounds_removal"] = confounds


class AtlasSeedDualRegBased(FeatureTemplate):
    """
    AtlasSeedDualRegBased is a superclass for managing Atlas, Seed and DualReg features.
    These three subclasses contains the tag_panel.

    Attributes
    ----------
    entity : str
        Descriptive representation of the feature.
    filters : dict
        Dictionary containing datatype and suffix filters.
    featurefield : str
        The field specifying atlases.
    type : str
        Type of the feature, in this case, "atlas_based_connectivity".
    file_panel_class : Type
        Class used for the file panel in the GUI.
    minimum_coverage_label : str
        Label text for minimum atlas region coverage by individual brain mask.

    Methods
    -------
    compose()
        Constructs the GUI layout for atlas-based connectivity.

    on_mount()
        Handles actions to be taken when the component is mounted in the GUI.
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "atlas"}
    featurefield = "atlases"
    type = "atlas_based_connectivity"
    file_panel_class = AtlasFilePanel
    minimum_coverage_label = "Minimum atlas region coverage by individual brain mask"

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            if self.images_to_use is not None:
                yield self.images_to_use_selection_panel
            yield self.file_panel_class(id="top_file_panel", classes="components file_panel")
            yield self.tag_panel
            yield LabelWithInputBox(
                label=self.minimum_coverage_label,
                value=self.feature_dict["min_region_coverage"],
                classes="switch_with_input_box components",
                id="minimum_coverage",
            )
            yield self.preprocessing_panel

    async def on_mount(self) -> None:
        try:
            self.get_widget_by_id("minimum_coverage").border_title = "Minimum coverage"
        except Exception:
            pass
        self.get_widget_by_id("tag_selection").border_title = self.filters["suffix"].capitalize() + " files"
        self.get_widget_by_id("top_file_panel").border_title = self.filters["suffix"].capitalize() + " seed images"

    @on(file_panel_class.Changed, "#top_file_panel")
    def on_file_panel_changed(self, message: Message):
        tagvals = set(self.tagvals)
        template_path = message.value["file_pattern"]
        if isinstance(template_path, Text):
            template_path = template_path.plain

        all_tagvals_based_on_the_current_file_patterns = set(
            [
                extract_name_part(template_path, file_path, suffix=self.filters["suffix"])
                for file_path in message.value["files"]
            ]
        )
        if all_tagvals_based_on_the_current_file_patterns == {None}:
            all_tagvals_based_on_the_current_file_patterns = set(
                [extract_name_part(template_path, file_path, suffix="desc") for file_path in message.value["files"]]
            )
        tagvals = tagvals ^ all_tagvals_based_on_the_current_file_patterns
        self.update_tag_selection_by_children_walk(tagvals)

    def update_tag_selection_by_children_walk(self, tagvals: set):
        for tagval in tagvals:
            self.get_widget_by_id("tag_selection").add_option(Selection(tagval, tagval, initial_state=True))


class AtlasBased(AtlasSeedDualRegBased):
    """
    A class used to represent Atlas-based connectivity analysis

    Attributes
    ----------
    entity : str
        A description of the entity, which in this context is "desc"
    filters : dict
        A dictionary containing filters for datatype and suffix
            - datatype: "ref"
            - suffix: "atlas"
    featurefield : str
        A field representing the atlas feature set, in this case "atlases"
    type : str
        The type of connectivity analysis, denoted as "atlas_based_connectivity"
    file_panel_class : class
        A reference to the class used for file panel, here it is AtlasFilePanel
    minimum_coverage_label : str
        A label describing the minimum coverage of atlas regions by individual brain mask
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "atlas"}
    featurefield = "atlases"
    type = "atlas_based_connectivity"
    file_panel_class = AtlasFilePanel
    minimum_coverage_label = "Minimum atlas region coverage by individual brain mask"


class SeedBased(AtlasSeedDualRegBased):
    """
    Inherits from AtlasSeedDualRegBased and represents a connectivity analysis
    using seed-based approach.

    Attributes
    ----------
    entity : str
        Description of the entity being analyzed.
    filters : dict
        Dictionary specifying filters for data type and suffix.
    featurefield : str
        Field name in the feature dataset.
    type : str
        Type of connectivity being analyzed.
    file_panel_class : type
        Class used for managing file panels.
    minimum_coverage_label : str
        Label for the minimum coverage requirement of seed map regions by
        individual brain masks.
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "seed"}
    featurefield = "seeds"
    type = "seed_based_connectivity"
    file_panel_class = SeedMapFilePanel
    minimum_coverage_label = "Minimum seed map region coverage by individual brain mask"


class DualReg(AtlasSeedDualRegBased):
    """
    class DualReg(AtlasSeedDualRegBased):
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "map"}
    featurefield = "maps"
    type = "dual_regression"
    file_panel_class = SpatialMapFilePanel
    minimum_coverage_label = "Minimum spatial map region coverage by individual brain mask"

    async def on_mount(self) -> None:
        self.get_widget_by_id("minimum_coverage").remove()


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

    _on_selection_list_changed_images_to_use_selection()
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

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        if "conditions" not in self.feature_dict:
            self.feature_dict["conditions"] = []
        if self.images_to_use is not None:
            all_possible_conditions = []
            for v in self.images_to_use["task"].keys():
                all_possible_conditions += extract_conditions(entity="task", values=[v])

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
                yield self.images_to_use_selection_panel
                yield self.model_conditions_and_contrast_table
            yield self.preprocessing_panel

    async def on_mount(self) -> None:
        if self.images_to_use is not None:
            self.get_widget_by_id("images_to_use_selection").border_title = "Images to use"
        if self.app.is_bids is not True:
            await self.mount(
                EventFilePanel(id="top_event_file_panel", classes="file_panel components"),
                after=self.get_widget_by_id("images_to_use_selection"),
            )
            self.get_widget_by_id("top_event_file_panel").border_title = "Event files patterns"

    @on(file_panel_class.Changed, "#top_event_file_panel")
    @on(SelectionList.SelectionToggled, "#images_to_use_selection")
    def _on_selection_list_changed_images_to_use_selection(self, message):
        # this has to be split because when making a subclass, the decorator causes to ignored redefined function in the
        # subclass

        # in the old UI if the user did not select any images, the UI did not let the user proceed further. Here we do
        # more-less the same. If there are no choices user gets an error and all options are selected again.
        if len(self.get_widget_by_id("images_to_use_selection").selected) == 0:
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
            self.get_widget_by_id("images_to_use_selection").select_all()

        # try to update it here? this refresh the whole condition list every time that image is changed
        all_possible_conditions = []
        if self.images_to_use is not None:
            for v in self.images_to_use["task"].keys():
                all_possible_conditions += extract_conditions(entity="task", values=[v])
            self.get_widget_by_id("model_conditions_and_constrasts").update_all_possible_conditions(all_possible_conditions)

            self.update_conditions_table()

    def update_conditions_table(self):
        condition_list = []
        for value in self.get_widget_by_id("images_to_use_selection").selected:
            condition_list += extract_conditions(entity="task", values=[value])

        self.setting_dict["filters"][0]["values"] = self.get_widget_by_id("images_to_use_selection").selected
        # force update of model_conditions_and_constrasts to reflect conditions given by the currently selected images
        self.get_widget_by_id("model_conditions_and_constrasts").condition_values = condition_list


class PreprocessedOutputOptions(TaskBased):
    """
    PreprocessedOutputOptions(this_user_selection_dict, **kwargs)

    Class for managing preprocessed image output options within a task-based framework.

    Parameters
    ----------
    this_user_selection_dict : dict
        Dictionary containing user selections.
    **kwargs
        Additional keyword arguments passed to the superclass.

    Methods
    -------
    on_mount()
        Async method to handle actions when the widget is mounted.
    """

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        # no features for preprocessed image output!
        this_user_selection_dict["features"] = {}

    async def on_mount(self) -> None:
        self.get_widget_by_id("model_conditions_and_constrasts").remove()  # .styles.visibility = "hidden"


class ReHo(FeatureTemplate):
    """
    ReHo

    A class that represents the Regional Homogeneity (ReHo) feature, which is a Measure of the similarity or coherence of the
    time series of a given voxel with its nearest neighbors.

    Attributes
    ----------
    type : str
        A string representing the type of the feature.

    Methods
    -------
    __init__(self, this_user_selection_dict, **kwargs)
        Initializes the ReHo feature with given user selection dictionary and keyword arguments.

    compose(self) -> ComposeResult
        Composes the user interface elements required for the ReHo feature.

    on_mount(self)
        Async method that is called when the ReHo feature is mounted in the application.
    """

    type = "reho"

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        # in this case, smoothing is in features!!!
        if "smoothing" not in self.feature_dict:
            self.feature_dict["smoothing"] = {"fwhm": 0}
        if "smoothing" in self.setting_dict:
            del self.setting_dict["smoothing"]

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            yield self.images_to_use_selection_panel
            yield self.preprocessing_panel

    async def on_mount(self) -> None:
        self.get_widget_by_id("images_to_use_selection").border_title = "Images to use"


class Falff(ReHo):
    """
    Falff(this_user_selection_dict, **kwargs)

    A class that represents the falff feature inheriting from ReHo and initializes
    specific unfiltered settings based on the user's selection dictionary.

    Parameters
    ----------
    this_user_selection_dict : dict
        Dictionary containing the user's selection.
    **kwargs : dict
        Additional keyword arguments passed to the ReHo initializer.

    Attributes
    ----------
    unfiltered_settings_dict : dict
        Dictionary containing settings specific to the unfiltered data derived
        from the user's selection dictionary.
    """

    type = "falff"

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        self.feature_dict["unfiltered_setting"] = self.feature_dict["name"] + "UnfilteredSetting"
        this_user_selection_dict["unfiltered_setting"]["name"] = self.feature_dict["name"] + "UnfilteredSetting"
        self.unfiltered_settings_dict = this_user_selection_dict["unfiltered_setting"]
