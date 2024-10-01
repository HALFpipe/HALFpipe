# -*- coding: utf-8 -*-
import copy
import os
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ...model.spec import load_spec
from ..feature_widgets.features import TaskBased
from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.event_file_widget import EventFilePanel

# from utils.false_input_warning_screen import FalseInputWarning
# from utils.confirm_screen import Confirm
from ..utils.filebrowser import FileBrowser, path_test_for_bids


class WorkDirectory(Widget):
    value: reactive[bool] = reactive(False, init=False)

    @dataclass
    class Changed(Message):
        work_directory: "WorkDirectory"
        value: bool

        @property
        def control(self):
            return self.work_directory

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(
                "Set path to the working directory. Here all output will be stored. By selecting a directory with existing \
spec.json file it is possible to load the therein configuration.",
                id="description",
            ),
            FileBrowser(path_to="WORKING DIRECTORY", id="work_dir_file_browser"),
            id="work_directory",
            classes="components",
        )

    async def on_file_browser_changed(self, message):
        async def working_directory_override(override):
            if override:
                await self.load_from_spec()
                self.value = True
            else:
                self.value = False
                self.get_widget_by_id("work_dir_file_browser").update_input(None)

        async def existing_spec_file_decision(load):
            if load:
                await self.load_from_spec()
                self.value = True
            else:
                self.app.push_screen(
                    Confirm(
                        "This action will override the existing spec in the selected working directory. Are you sure?",
                        title="Override existing working directory",
                        id="confirm_override_spec_file_modal",
                        classes="confirm_warning",
                    ),
                    working_directory_override,
                )
                self.value = False

        if os.path.isdir(message.selected_path):
            self.get_widget_by_id("work_dir_file_browser").styles.border = ("solid", "green")
            # show tabs
            self.app.flags_to_show_tabs["from_working_dir_tab"] = True
            self.app.show_hidden_tabs()

            ctx.workdir = message.selected_path
            self.existing_spec = load_spec(workdir=ctx.workdir)
            if self.existing_spec is not None:
                self.app.push_screen(
                    Confirm(
                        "Existing spec file was found! Do you want to load the settings or override the working directory?",
                        title="Spec file found",
                        left_button_text="Load",
                        right_button_text="Override",
                        id="confirm_spec_load_modal",
                        classes="confirm_warning",
                    ),
                    existing_spec_file_decision,
                )
            else:
                self.value = False
        else:
            self.get_widget_by_id("work_dir_file_browser").styles.border = ("solid", "red")

    def on_mount(self) -> None:
        self.get_widget_by_id("work_directory").border_title = "Select working directory"
        self.disabled = False

    # self.mount(EventFilePanel(id="top_event_file_panel", classes="components"))

    async def load_from_spec(self):
        """Feed the user_selections_dict with settings from the json file via the context object."""
        # First feed the cache

        #        self.app.flags_to_show_tabs["from_input_data_tab"] = True
        #        self.app.show_hidden_tabs()
        data_input_widget = self.app.get_widget_by_id("input_data_content")
        feature_widget = self.app.get_widget_by_id("feature_selection_content")
        tab_manager_widget = self.app.get_widget_by_id("tabs_manager")
        #   event_file_panel_widget = self.get_widget_by_id('top_event_file_panel')

        if self.existing_spec is not None:
            self.app.get_widget_by_id("input_data_content").toggle_bids_non_bids_format(False)
            event_file_objects = []
            for f in self.existing_spec.files:
                print("dddddddddddddddddddddir", dir(f))
                if f.datatype == "bids":
                    ctx.cache["bids"]["files"]["path"] = f.path
                    # this is the function used when we are loading bids data files, in also checks if the data
                    # folder contains bids files, and if yes, then it also extracts the tasks (images)
                    path_test_for_bids(f.path)
                    self.app.get_widget_by_id("input_data_content").toggle_bids_non_bids_format(True)
                # need to create a FileItem widgets for all non-bids files
                elif f.suffix == "bold":
                    await data_input_widget.add_bold_image(load_object=f)
                elif f.suffix == "T1w":
                    await data_input_widget.add_t1_image(load_object=f)
                elif f.suffix == "events":
                    print("ffffffffffffffffffound event file!!!!!!!!!", f)
                    event_file_objects.append(f)

            bold_filedict = {"datatype": "func", "suffix": "bold"}
            filepaths = ctx.database.get(**bold_filedict)
            ctx.refresh_available_images()

            print("load_from_specload_from_specload_from_spec filepaths", filepaths)

            data_input_widget.feed_contex_and_extract_available_images()
            # show hidden tabs using this, it is not how i wanted it but at least it works
            tab_manager_widget.show_tab("preprocessing_tab")
            tab_manager_widget.show_tab("feature_selection_tab")
            tab_manager_widget.show_tab("models_tab")

            for feature in self.existing_spec.features:
                print("self.existing_spec.featuresself.existing_spec.features", feature.__dict__)
                ctx.cache[feature.name]["features"] = copy.deepcopy(feature.__dict__)
            for setting in self.existing_spec.settings:
                print("settingsettingsettingsettingsettingsettingsetting", setting, dir(setting))
                # the feature settings in the ctx.cache are under the 'feature' key, to match this properly
                # setting['name'[ is used without last 7 letters which are "Setting" then it is again the feature name
                ctx.cache[setting["name"][:-7]]["settings"] = setting
            # Then create the widgets
            for top_name in ctx.cache:
                if ctx.cache[top_name]["features"] != {}:
                    print("ctx.cache[top_name]['features']ctx.cache[top_name]['features']", ctx.cache[top_name]["features"])
                    name = ctx.cache[top_name]["features"]["name"]
                    print("namenamenamename", name)
                    print(
                        'ctx.cache[name]["features"]["type"]ctx.cache[name]["features"]["type"]',
                        ctx.cache[name]["features"]["type"],
                    )
                    print('[ctx.cache[name]["features"][ctx.cache[name]["features"]', ctx.cache[name]["features"])
                    # how to solve this?
                    await feature_widget.add_new_feature([ctx.cache[name]["features"]["type"], name])

            for event_file_object in event_file_objects:
                print("---------feature_widget .walk_children  (EventFilePanel)", feature_widget.walk_children(TaskBased))
                print("event_file_object.extension")
                print(
                    "walk2", feature_widget.walk_children(TaskBased)[0].walk_children()
                )  # query_one(EventFilePanel).create_file_item(load_object=event_file_object)
                await (
                    feature_widget.walk_children(TaskBased)[0]
                    .query_one(EventFilePanel)
                    .create_file_item(load_object=event_file_object)
                )
        #                           await event_file_panel_widget.create_file_item(load_object=f)

        print("wwwwwwwwwwwwwwwwwworking dir self.app.available_images", self.app.available_images)

    def watch_value(self) -> None:
        self.post_message(self.Changed(self, self.value))

    # is this needed???????/
    # def on_work_directory_changed(self, message):
    # """When a path to a directory with existing json file is selected, the Context object and available images
    # are fed via the input_data_content widget.
    # """
    # if message.value:
    # self.get_widget_by_id("input_data_content").feed_contex_and_extract_available_images()
    # self.get_widget_by_id("input_data_content").manually_change_label(ctx.cache["bids"]["files"]["path"])
    # for name in ctx.cache:
    # # Need to avoid key 'files' in the dictionary, since this only key is not a feature.
    # if name != "files":
    # self.get_widget_by_id("feature_selection_content").add_new_feature(
    # [ctx.cache[name]["features"]["type"], name]  # type: ignore[index]
    # )
