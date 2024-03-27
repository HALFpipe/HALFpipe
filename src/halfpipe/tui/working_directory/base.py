# -*- coding: utf-8 -*-
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from ...model.spec import load_spec

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
        app,
        ctx,
        user_selections_dict: dict,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.top_parent = app
        self.ctx = ctx
        self.user_selections_dict: dict = user_selections_dict

    def compose(self) -> ComposeResult:
        yield Grid(
            FileBrowser(app=self.top_parent, path_to="working directory", id="work_dir_file_browser"),
            id="work_directory",
            classes="components",
        )

    def on_file_browser_changed(self, message):
        self.ctx.workdir = message.selected_path
        self.existing_spec = load_spec(workdir=self.ctx.workdir)

        if self.existing_spec is not None:
            self.user_selections_from_spec()
            self.value = True
        else:
            self.value = False

    def user_selections_from_spec(self):
        """Feed the user_selections_dict with settings from the json file via the context object."""
        if self.existing_spec is not None:
            self.user_selections_dict["files"]["path"] = self.existing_spec.files[0].path
            for feature in self.existing_spec.features:
                for method_name in ["conditions", "contrasts", "high_pass_filter_cutoff", "hrf", "name", "setting", "type"]:
                    self.user_selections_dict[feature.name]["features"][method_name] = getattr(feature, method_name)

                for setting in self.existing_spec.settings:
                    if setting["name"] == self.user_selections_dict[feature.name]["features"]["setting"]:
                        for key in setting:
                            self.user_selections_dict[feature.name]["settings"][key] = setting[key]

    def watch_value(self) -> None:
        self.post_message(self.Changed(self, self.value))
