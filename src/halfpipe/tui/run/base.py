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
from ..utils.context import ctx


class RunCLX(Widget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        #  self.top_parent = app
        #  self.ctx = ctx

    #  ctx.cache = user_selections_dict

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield Pretty("", id="this_output")
            yield Button("Refresh")

    def on_button_pressed(self):
        self.dump_dict_to_contex()
        self.get_widget_by_id("this_output").update(
            json.loads(SpecSchema().dumps(ctx.spec, many=False, indent=4, sort_keys=False))
        )

    def dump_dict_to_contex(self):
        print("ccccccccccccccccccc", ctx.cache)
        ctx.spec.features.clear()
        ctx.spec.settings.clear()
        print("uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu", ctx.cache)
        for name in ctx.cache:
            if name != "files":
                # for preprocessed image output there are no features, thus the dict is empty
                if ctx.cache[name]["features"] != {}:
                    featureobj = Feature(name=name, type=ctx.cache[name]["features"]["type"])
                    ctx.spec.features.append(featureobj)
                # for settings
                settingdict: dict = {}
                setting = {**settingdict}
                setting["name"] = ctx.cache[name]["settings"]["name"]
                ctx.spec.settings.append(SettingSchema().load(setting, partial=True))
                # here it is ok, because since it is empty, there are no iterations
                for key in ctx.cache[name]["features"]:
                    try:
                        setattr(ctx.spec.features[-1], key, ctx.cache[name]["features"][key])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                for key in ctx.cache[name]["settings"]:
                    try:
                        setattr(ctx.spec.settings[-1], key, ctx.cache[name]["settings"][key])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
        # print('ccccccccccccccccccccccccccccccc ctx.spec.files', [f.path for f in ctx.spec.files])
        # #try:
        # print('1111111111ccccccccccccccccccccc', ctx.database.fromspecfileobj(ctx.spec.files[-1]))
        # la =  ctx.database.fromspecfileobj(ctx.spec.files[-1])
        # if la is not None:
        # print('2222ccccccccccccccccccccccc',[f.path for f in ctx.database.fromspecfileobj(ctx.spec.files[-1])])
        # #except:
        # #   print('failed')
