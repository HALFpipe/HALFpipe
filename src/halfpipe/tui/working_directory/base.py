# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ...model.spec import load_spec
from ..utils.confirm_screen import Confirm
from ..utils.context import ctx

# from utils.false_input_warning_screen import FalseInputWarning
# from utils.confirm_screen import Confirm
from ..utils.filebrowser import FileBrowser


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
        #    user_selections_dict: dict,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)

    #      self.top_parent = app
    #   self.user_selections_dict: dict = user_selections_dict

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

    def on_file_browser_changed(self, message):
        def working_directory_override(override):
            if override:
                self.user_selections_from_spec()
                self.value = True
            else:
                self.value = False
                self.get_widget_by_id("work_dir_file_browser").update_input(None)

        def existing_spec_file_decision(load):
            if load:
                self.user_selections_from_spec()
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

    def user_selections_from_spec(self):
        """Feed the user_selections_dict with settings from the json file via the context object."""
        if self.existing_spec is not None:
            ctx.cache["bids"]["files"]["path"] = self.existing_spec.files[0].path
            for feature in self.existing_spec.features:
                for method_name in ["conditions", "contrasts", "high_pass_filter_cutoff", "hrf", "name", "setting", "type"]:
                    ctx.cache[feature.name]["features"][method_name] = getattr(feature, method_name)

                for setting in self.existing_spec.settings:
                    if setting["name"] == ctx.cache[feature.name]["features"]["setting"]:
                        for key in setting:
                            ctx.cache[feature.name]["settings"][key] = setting[key]

    def watch_value(self) -> None:
        self.post_message(self.Changed(self, self.value))
