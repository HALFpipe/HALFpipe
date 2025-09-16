import copy
from collections import defaultdict

from ..logging import logger
from .data_analyzers.context import ctx
from .data_analyzers.file_pattern_steps import (
    FieldMapStep,
    Magnitude1Step,
    Magnitude2Step,
    Phase1Step,
    Phase2Step,
    PhaseDiffStep,
)
from .features.atlas_based import AtlasBased
from .features.dual_reg import DualReg
from .features.preproc_output import PreprocessedOutputOptions
from .features.seed_based import SeedBased
from .features.task_based import TaskBased
from .help_functions import widget_exists
from .specialized_widgets.confirm_screen import Confirm
from .specialized_widgets.event_file_widget import AtlasFilePanel, EventFilePanel, SeedMapFilePanel, SpatialMapFilePanel
from .specialized_widgets.filebrowser import path_test_for_bids
from .specialized_widgets.non_bids_file_itemization import FileItem

# define this map for the load purposes
field_map_to_pattern_map = {
    "magnitude1": Magnitude1Step,
    "magnitude2": Magnitude2Step,
    "phase1": Phase1Step,
    "phase2": Phase2Step,
    "phasediff": PhaseDiffStep,
    "fieldmap": FieldMapStep,
}


def replace_with_longnames(f):
    entity_longnames = {"subject": "sub", "session": "ses"}
    if f.suffix in ["atlas", "seed", "map"]:
        entity_longnames[f.suffix] = "desc"
    input_string = f.path
    for long, short in entity_longnames.items():
        input_string = input_string.replace(f"{{{short}}}", f"{{{long}}}")
    f.path = input_string
    return f


async def fill_ctx_spec(self):
    """
    Loads settings from the 'spec.json' file into the context spec object.

    This method reads the settings from the 'spec.json' file (if it
    exists) and populates the context cache with the loaded data.
    This includes global settings, file patterns, feature settings,
    and model settings.
    """
    # First feed the cache
    if self.existing_spec is not None:  # Add this check
        global_settings = self.existing_spec.global_settings
        files = self.existing_spec.files
        settings = self.existing_spec.settings
        features = self.existing_spec.features
        models = self.existing_spec.models

        ctx.spec.global_settings = global_settings
        for fileobj in files:
            ctx.put(fileobj)
        ctx.spec.settings = settings
        ctx.spec.features = features
        ctx.spec.models = models

        # cache_file_patterns(self)


async def cache_file_patterns(self):
    """
    Caches file patterns and settings from the spec file.

    This method is a worker that processes the loaded specification
    and caches the file patterns and settings in the context. It also
    creates the corresponding widgets for data input, preprocessing,
    feature selection, and model selection.
    """

    def format_fmap_associations(data):
        output = []
        for session, tasks in data.items():
            if session == "acq.null":
                continue
            task_list = ", ".join(tasks)
            output.append(f"{session}: {task_list}")
        return "\n".join(output)

    data_input_widget = self.app.get_widget_by_id("input_data_content")
    # Suppress actions done when switch is toggled. We do the mounting directly by calling the method.
    data_input_widget.supress_switch_events()
    self.data_input_widget = data_input_widget

    preprocessing_widget = self.app.get_widget_by_id("preprocessing_content")
    self.feature_widget = self.app.get_widget_by_id("feature_selection_content")
    self.model_widget = self.app.get_widget_by_id("models_content")

    # The philosophie here is that we copy the data from the existing spec file to the context cache and then create
    # corresponding widgets. Through these widgets then it should be possible to further modify the spec file.
    # The created widgets should avoid using step and meta classes upon creation as these triggers various user choice
    # modals.
    if self.existing_spec is not None:
        spreadsheet_counter = 0
        fmaps = False
        intended_for = ""
        self.event_file_objects = []
        self.atlas_file_objects = []
        self.seed_map_file_objects = []
        self.spatial_map_file_objects = []

        preprocessing_widget.default_settings = self.existing_spec.global_settings
        preprocessing_widget.refresh(recompose=True)

        # We want to start with non-bids and switch to bids, because if it is bids data then basically, except for the
        # possible lesion maps, there will be only one file object and that would be the file to the bids data.
        # To make sure that the format is set to non-bids we check by this 'if' if the user did not already switch it.
        if self.app.is_bids:
            await data_input_widget.toggle_bids_non_bids_format(False)
            data_input_widget.get_widget_by_id("bids_non_bids_switch").value = False

        for f in self.existing_spec.files:
            logger.debug(f"UI->load->cache_file_patterns-> Processing file object {f.__dict__}")

            # In the spec file, subject is abbreviated to 'sub' and atlas, seed and map is replaced by desc,
            # here we replace it back for the consistency.
            f = replace_with_longnames(f)

            if f.datatype == "bids":
                await data_input_widget._build_and_mount_bids_panels()
                await data_input_widget.get_widget_by_id("non_bids_panel").remove()
                self.app_is_bids = True
                # Flip the switch
                data_input_widget.get_widget_by_id("bids_non_bids_switch").value = True

                ctx.cache["bids"]["files"] = f.path
                data_input_widget.get_widget_by_id("data_input_file_browser").update_input(f.path)
                # this is the function used when we are loading bids data files, in also checks if the data
                # folder contains bids files, and if yes, then it also extracts the tasks (images)
                path_test_for_bids(f.path)
            # need to create a FileItem widgets for all non-bids files
            elif f.datatype == "spreadsheet":
                ctx.cache["__spreadsheet_file_" + str(spreadsheet_counter)]["files"] = f
                spreadsheet_counter += 1
            elif f.suffix == "bold":
                message_dict = {i: [str(f.metadata[i])] for i in f.metadata} if f.metadata is not None else None
                widget_name = await data_input_widget.add_bold_image(
                    load_object=f, message_dict=message_dict, execute_pattern_class_on_mount=False
                )
                ctx.cache[widget_name]["files"] = f
            elif f.suffix == "T1w":
                widget_name = await data_input_widget.add_t1_image(
                    load_object=f, message_dict=None, execute_pattern_class_on_mount=False
                )
                ctx.cache[widget_name]["files"] = f
            elif f.suffix == "T2w":
                widget_name = await data_input_widget.add_t2_image(
                    load_object=f, message_dict=None, execute_pattern_class_on_mount=False
                )
                ctx.cache[widget_name]["files"] = f
            elif f.suffix == "roi" or f.suffix == "mask":
                if not widget_exists(data_input_widget, "lesion_mask_pattern_panel"):
                    await data_input_widget.toggle_lesion_mask_panel(True)
                    data_input_widget.get_widget_by_id("lesion_mask_switch").value = True

                widget_name = await data_input_widget.add_lesion_mask(
                    load_object=f, message_dict=None, execute_pattern_class_on_mount=False
                )
                ctx.cache[widget_name]["files"] = f
            elif f.datatype == "fmap":
                message_dict = {i: [str(f.metadata[i])] for i in f.metadata} if f.metadata is not None else None
                fmap_file_pattern = field_map_to_pattern_map[f.suffix]
                widget_name = await data_input_widget.add_field_map(
                    pattern_class=fmap_file_pattern,
                    load_object=f,
                    message_dict=message_dict,
                    execute_pattern_class_on_mount=False,
                )
                ctx.cache[widget_name]["files"] = f
                fmaps = True
                # Gather bold files - fmaps association only from magnitude files, to avoid duplication
                if f.suffix == "magnitude1":
                    intended_for += format_fmap_associations(f.intended_for)

            elif f.suffix == "events":
                self.event_file_objects.append(f)
            elif f.suffix == "atlas":
                self.atlas_file_objects.append(f)
            elif f.suffix == "seed":
                self.seed_map_file_objects.append(f)
            elif f.suffix == "map":
                self.spatial_map_file_objects.append(f)

        ctx.refresh_available_images()
        if self.app.is_bids:
            data_input_widget.update_summaries()
        if ctx.get_available_images == {}:
            self.data_input_success = await self.app.push_screen_wait(
                Confirm(
                    "No bold files found! The data input directory in \n"
                    "the spec.json seems to be not available on your computer!",
                    title="Error",
                    left_button_text=False,
                    right_button_text="OK",
                    id="input_data_directory_error_modal",
                    classes="confirm_error",
                )
            )
            # clear all inputs, basically restart the inputs on the TUI
            for file_item in self.app.walk_children(FileItem):
                file_item.remove()
            ctx.cache = defaultdict(lambda: defaultdict(dict))
            self.app.flags_to_show_tabs["from_input_data_tab"] = False
            self.app.flags_to_show_tabs["from_working_dir_tab"] = False
            self.app.hide_tabs()
            self.get_widget_by_id("work_dir_file_browser").update_input("")
            ctx.workdir = None
        else:
            self.app.flags_to_show_tabs["from_input_data_tab"] = True
            self.app.show_hidden_tabs()
            self.data_input_success = True

        if fmaps:
            data_input_widget.get_widget_by_id("associate_button").styles.visibility = "visible"
            data_input_widget.get_widget_by_id("info_field_maps_button").styles.visibility = "visible"
            data_input_widget.callback_message = intended_for


async def mount_features(self):
    """
    Mounts the feature selection widgets based on the loaded spec file.

    This method is a worker that creates and mounts the feature
    selection widgets based on the features defined in the loaded
    specification. It populates the context cache with feature and
    setting data and then adds the corresponding widgets to the UI.
    """
    feature_widget = self.feature_widget
    setting_feature_map = {}
    if self.existing_spec is not None:
        for feature in self.existing_spec.features:
            logger.debug(f"UI->load->mount_features-> Processing feature {feature.__dict__}")

            ctx.cache[feature.name]["features"] = copy.deepcopy(feature.__dict__)
            setting_feature_map[feature.__dict__["setting"]] = feature.name

        for setting in self.existing_spec.settings:
            logger.debug(f"UI->load->mount_features-> Processing setting {setting.__dict__}")

            # the feature settings in the ctx.cache are under the 'feature' key, to match this properly
            # setting['name'[ is used without last 7 letters which are "Setting" then it is again the feature name

            if not setting["output_image"]:
                # In case of falff, there is also unfiltered setting which is essentially the same as normal setting
                # but without the bandpass filter. So we put only the normal setting into the cache because in the run
                # tab the unfiltered setting will be created automatically form the normal setting.
                if setting["name"] in setting_feature_map:
                    ctx.cache[setting_feature_map[setting["name"]]]["settings"] = copy.deepcopy(setting)
            else:
                ctx.cache[setting["name"]]["features"] = {}
                ctx.cache[setting["name"]]["settings"] = copy.deepcopy(setting)
                ctx.cache[setting["name"]]["settings"].setdefault("smoothing", {"fwhm": None})

                ctx.cache[setting["name"]]["settings"].setdefault("grand_mean_scaling", {"mean": None})
                ctx.cache[setting["name"]]["settings"].setdefault("bandpass_filter", {"type": None})

            if setting["name"] in setting_feature_map:
                cache_entry: dict = ctx.cache.get(setting_feature_map[setting["name"]], {})

                if isinstance(cache_entry, dict):
                    settings = cache_entry.get("settings", {})
                    feature = cache_entry.get("features", {})
                else:
                    settings = {}
                    feature = {}
                # Add default smoothing settings if missing
                if feature["type"] == "falff" or feature["type"] == "reho":
                    feature.setdefault("smoothing", {"fwhm": None})
                else:
                    settings.setdefault("smoothing", {"fwhm": None})

                settings.setdefault("grand_mean_scaling", {"mean": None})
                settings.setdefault("bandpass_filter", {"type": None})

        # Then create the widgets
        for top_name in ctx.cache:
            if ctx.cache[top_name]["features"] != {}:
                name = ctx.cache[top_name]["features"]["name"]
                await feature_widget.add_new_item([ctx.cache[name]["features"]["type"], name])
            # ctx.cache[top_name]["features"] is empty {} dir in case of preproc feature, then we look if there is at least
            # the settings key indicating that this is not a file pattern but a preproc feature
            elif ctx.cache[top_name]["settings"] != {}:
                name = ctx.cache[top_name]["settings"]["name"]
                await feature_widget.add_new_item(["preprocessed_image", name.replace("Setting", "")])


async def mount_file_panels(self) -> None:
    """
    Initializes file panels for various file types.

    This method is a worker that creates and mounts file panels for
    different file types (events, atlas, seed, spatial maps) based on
    the loaded specification. It iterates through the file objects and
    creates corresponding file panel widgets, adding them to the
    appropriate feature widgets.
    """
    feature_widget = self.feature_widget

    for file_object in self.event_file_objects:
        message_dict = {i: [str(file_object.metadata[i])] for i in file_object.metadata}
        for task_based_widget in feature_widget.walk_children(TaskBased):
            # there is no event file panel in PreprocessedOutputOptions
            if type(task_based_widget) is not PreprocessedOutputOptions:
                widget_name = await task_based_widget.query_one(EventFilePanel).create_file_item(
                    load_object=file_object, message_dict=message_dict
                )
        ctx.cache[widget_name]["files"] = file_object

    for file_object in self.atlas_file_objects:
        message_dict = {i: [str(file_object.metadata[i])] for i in file_object.metadata}
        for atlas_based_widget in feature_widget.walk_children(AtlasBased):
            widget_name = await atlas_based_widget.query_one(AtlasFilePanel).create_file_item(
                load_object=file_object, message_dict=message_dict
            )
        ctx.cache[widget_name]["files"] = file_object

    for file_object in self.seed_map_file_objects:
        message_dict = {i: [str(file_object.metadata[i])] for i in file_object.metadata}
        for seed_based_widget in feature_widget.walk_children(SeedBased):
            widget_name = await seed_based_widget.query_one(SeedMapFilePanel).create_file_item(
                load_object=file_object, message_dict=message_dict
            )
        ctx.cache[widget_name]["files"] = file_object

    for file_object in self.spatial_map_file_objects:
        message_dict = {i: [str(file_object.metadata[i])] for i in file_object.metadata}
        for dual_reg_widget in feature_widget.walk_children(DualReg):
            widget_name = await dual_reg_widget.query_one(SpatialMapFilePanel).create_file_item(
                load_object=file_object, message_dict=message_dict
            )
        ctx.cache[widget_name]["files"] = file_object


async def mount_models(self) -> None:
    """
    Initializes the model selection widgets based on the loaded spec file.

    This method is a worker that creates and mounts the model selection
    widgets based on the models defined in the loaded specification. It
    populates the context cache with model data and also creates aggregate
    model entries.
    """
    # this is better to put here so that within the async it is not triggered earlier
    self.data_input_widget.enable_switch_events()

    model_widget = self.model_widget
    aggregate_models = {}
    if self.existing_spec is not None:
        for model in self.existing_spec.models:
            logger.debug(f"UI->load->mount_models-> Processing model {model.__dict__}")

            # With aggregate models we deal differently, we do not create a widget for them, but instead create a dummy
            # entry in cache associated with a particular widget.
            if model.__dict__["type"] != "fe":
                ctx.cache[model.name]["models"] = copy.deepcopy(model.__dict__)
            else:
                # gather all available aggregate models
                aggregate_models[model.__dict__["name"]] = copy.deepcopy(model.__dict__)

        # Now we will create the aggregate model dummy association mentioned above.
        aggregate_cache_dummy_entries = {}
        for _, model_entry in ctx.cache.items():
            model = model_entry["models"]
            if model != {}:  # Check if model is not empty
                # Aggregate model dummy association
                associated_aggregate_models_list = []
                dummy_cache_key = model["name"] + "__aggregate_models_list"

                # Process each input label in the model's inputs
                for input_label in model.get("inputs", []):  # Ensure "inputs" exists
                    while input_label and input_label.startswith("aggregate") and "Across" in input_label:
                        if input_label in aggregate_models:
                            # this will select a particular model in the aggregate_models dictionary created before
                            aggregate_model = aggregate_models[input_label]
                            associated_aggregate_models_list.append(aggregate_model)
                            input_label = aggregate_model["inputs"][0] if aggregate_model["inputs"] else None
                        else:
                            break  # Stop if input_label is not found in aggregate_models

                # Put the associated aggregate models to this temporary dictionary to not modify cache while looping.
                aggregate_cache_dummy_entries[dummy_cache_key] = associated_aggregate_models_list

                # Then create the widgets
                await model_widget.add_new_item([model["type"], model["name"]])

        # Create the dummy entry in the cache, this needs to be done after the loop to not modify the cache when we are
        # looping over it
        for dummy_cache_key, aggregate_model in aggregate_cache_dummy_entries.items():
            ctx.cache[dummy_cache_key]["models"] = {"aggregate_models_list": aggregate_model}
