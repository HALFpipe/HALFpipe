# -*- coding: utf-8 -*-
import json
import sys
import traceback

from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Pretty

from ...model.feature import Feature
from ...model.setting import SettingSchema

# from utils.false_input_warning_screen import FalseInputWarning
# from utils.confirm_screen import Confirm
from ...model.spec import SpecSchema


class RunCLX(Widget):
    def __init__(self, app, ctx, user_selections_dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.top_parent = app
        self.ctx = ctx
        self.user_selections_dict = user_selections_dict

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield Pretty("", id="this_output")
            yield Button("Refresh")

    def on_button_pressed(self):
        self.dump_dict_to_contex()
        self.get_widget_by_id("this_output").update(
            json.loads(SpecSchema().dumps(self.ctx.spec, many=False, indent=4, sort_keys=False))
        )

    def dump_dict_to_contex(self):
        self.ctx.spec.features.clear()
        self.ctx.spec.settings.clear()

        for name in self.user_selections_dict:
            if name != "files":
                featureobj = Feature(name=name, type=self.user_selections_dict[name]["features"]["type"])
                self.ctx.spec.features.append(featureobj)
                # for settings
                settingdict: dict = {}
                setting = {**settingdict}
                setting["name"] = self.user_selections_dict[name]["settings"]["name"]
                self.ctx.spec.settings.append(SettingSchema().load(setting, partial=True))
                for key in self.user_selections_dict[name]["features"]:
                    try:
                        setattr(self.ctx.spec.features[-1], key, self.user_selections_dict[name]["features"][key])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                for key in self.user_selections_dict[name]["settings"]:
                    try:
                        setattr(self.ctx.spec.settings[-1], key, self.user_selections_dict[name]["settings"][key])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
