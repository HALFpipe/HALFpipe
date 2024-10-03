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
from textual import on, work

from ...model.spec import load_spec
from ..feature_widgets.features import TaskBased
from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.event_file_widget import EventFilePanel
from ..utils.filebrowser import FileBrowser, path_test_for_bids

from inflection import humanize
from typing import TYPE_CHECKING, Any, Iterable, Iterator
from textual.worker import Worker, WorkerState, WorkType
import asyncio

class WorkDirectory(Widget):

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

    def on_mount(self) -> None:
        self.get_widget_by_id("work_directory").border_title = "Select working directory"
        self.disabled = False

    @on(FileBrowser.Changed)
    async def _on_file_browser_changed(self, message: Message):
        '''The FileBrowser itself makes checks over the selected working directory validity. If it passes then we get here
        and no more checks are needed.
        '''
        # Change border to green
        self.get_widget_by_id("work_dir_file_browser").styles.border = ("solid", "green")
        # add flag signaling that the working directory was set
        self.app.flags_to_show_tabs["from_working_dir_tab"] = True
        self.app.show_hidden_tabs()
        async def working_directory_override(override):
            '''Function about overriding the found existing spec files'''
            if override:
                await self.load_from_spec()
            else:
                self.get_widget_by_id("work_dir_file_browser").update_input(None)

        async def existing_spec_file_decision(load):
            '''Function making user aware that there is an existing spec file in the selected working directory
            and whether he/she wants to load it.
            '''
            if load:
                await self.load_from_spec()
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
        # add path to context object
        ctx.workdir = message.selected_path
        # Load the spec and by this we see whether there is existing spec file or not
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


    async def load_from_spec(self):
        """Feed the user_selections_dict with settings from the json file via the context object."""
        # First feed the cache
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

        self.cache_file_patterns()

        #     print('ccccccccccccccccccccccccccccccccccccccccccccccccccccache', ctx.cache)
        #
        #     print("load_from_specload_from_specload_from_spec filepaths", filepaths)
        #
        #     # show hidden tabs using this, it is not how i wanted it but at least it works
        #     tab_manager_widget.show_tab("preprocessing_tab")
        #     tab_manager_widget.show_tab("feature_selection_tab")
        #     tab_manager_widget.show_tab("models_tab")
        #

        # #
    @work(exclusive=True, name='cache_file_worker')
    async def cache_file_patterns(self):
        data_input_widget = self.app.get_widget_by_id("input_data_content")
        feature_widget = self.app.get_widget_by_id("feature_selection_content")
        tab_manager_widget = self.app.get_widget_by_id("tabs_manager")
        #   event_file_panel_widget = self.get_widget_by_id('top_event_file_panel')

        # The philosophie here is that we copy the data from the existing spec file to the context cache and then create
        # corresponging widgets. Through these widgets then it should be possible to further modify the spec file.
        # The created widgets should avoid using step and meta classes upon creation as these triggers various user choice
        # modals.
        if self.existing_spec is not None:
            self.app.get_widget_by_id("input_data_content").toggle_bids_non_bids_format(False)
            self.event_file_objects = []
            for f in self.existing_spec.files:
                if f.datatype == "bids":
                    ctx.cache["bids"]["files"] = f.path
                    data_input_widget.get_widget_by_id('data_input_file_browser').update_input(f.path)
                    print('////////////////////////////////////////////////', f.path)
                    # this is the function used when we are loading bids data files, in also checks if the data
                    # folder contains bids files, and if yes, then it also extracts the tasks (images)
                    path_test_for_bids(f.path)
                    self.app.get_widget_by_id("input_data_content").toggle_bids_non_bids_format(True)
                # need to create a FileItem widgets for all non-bids files
                elif f.suffix == "bold":
                    message_dict = {i: [str(f.metadata[i])] for i in f.metadata if i == 'repetition_time'}
                    widget_name = await data_input_widget.add_bold_image(pattern_class=False, load_object=f, message_dict=message_dict)
                    ctx.cache[widget_name]["files"] = f

                    print('ffffffffffffffffffffffffffffffffffffffff bold load object', f.__dict__)
                elif f.suffix == "T1w":
                    widget_name = await data_input_widget.add_t1_image(pattern_class=False, load_object=f, message_dict=None)
                    ctx.cache[widget_name]["files"] = f
                elif f.suffix == "events":
                    # print("ffffffffffffffffffound event file!!!!!!!!!", f)
                    self.event_file_objects.append(f)

            bold_filedict = {"datatype": "func", "suffix": "bold"}
            filepaths = ctx.database.get(**bold_filedict)
            print('filepathsfilepathsfilepathsfilepathsfilepathsfilepaths', filepaths)
            ctx.refresh_available_images()
            data_input_widget.update_summaries()

    @work(exclusive=True, name='feature_worker')
    async def mount_features(self):
        feature_widget = self.app.get_widget_by_id("feature_selection_content")

        setting_feature_map = {}
        for feature in self.existing_spec.features:
            # print("self.existing_spec.featuresself.existing_spec.features", feature.__dict__)
            ctx.cache[feature.name]["features"] = copy.deepcopy(feature.__dict__)
            setting_feature_map[feature.__dict__['setting']] = feature.name
        for setting in self.existing_spec.settings:
            print("settingsettingsettingsettingsettingsettingsetting", setting, setting["name"])
            print("settingsettingsettingsettingsettingsettingsetting name", setting["name"])
            # the feature settings in the ctx.cache are under the 'feature' key, to match this properly
            # setting['name'[ is used without last 7 letters which are "Setting" then it is again the feature name
            #  ctx.cache[setting["name"][:-7]]["settings"] = setting
            if setting['output_image'] is not True:
                ctx.cache[setting_feature_map[setting["name"]]]["settings"] = copy.deepcopy(setting)
            else:
                ctx.cache[setting["name"]]["features"] = {}
                ctx.cache[setting["name"]]["settings"] = copy.deepcopy(setting)

    #     # Then create the widgets
        print('fffffffffffffffffffffffffffffffirst time cache printtttttttttttttttttttt', ctx.cache)
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
        print('sssssssssssssssssssssecond time cache printtttttttttttttttttttt', ctx.cache)

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        print('test', event.handler_name)
        print('test', event.namespace)
        print('test', event.worker.name)
        print('test', event.state)
        if event.state == WorkerState.SUCCESS:
            if event.worker.name == 'cache_file_worker':
                print('i am finished with the taaaaaaaaaaask')
                self.mount_features()
            if event.worker.name == 'feature_worker':
                print('i am finished with the taaaaaaaaaaask')
                await self.mount_file_panels()


    async def mount_file_panels(self):
        feature_widget = self.app.get_widget_by_id("feature_selection_content")
        for event_file_object in self.event_file_objects:
                # print("---------feature_widget .walk_children  (EventFilePanel)", feature_widget.walk_children(TaskBased))
                # print("event_file_object.extension")
                # print(
                #     "walk2", feature_widget.walk_children(TaskBased)[0].walk_children()
                # )  # query_one(EventFilePanel).create_file_item(load_object=event_file_object)
                await (
                    feature_widget.walk_children(TaskBased)[0]
                    .query_one(EventFilePanel)
                    .create_file_item(load_object=event_file_object)
                )
                print('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb query_one(EventFilePanel) ID', feature_widget.walk_children(TaskBased)[0].query_one(EventFilePanel).id)
        # print("wwwwwwwwwwwwwwwwwworking dir self.app.available_images", self.app.available_images)