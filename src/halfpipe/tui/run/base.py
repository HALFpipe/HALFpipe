# -*- coding: utf-8 -*-
import copy
import json
import sys
import traceback
from collections import defaultdict
from typing import Any

import pandas as pd
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Pretty

from ...model.feature import Feature
from ...model.file.bids import BidsFileSchema
from ...model.setting import SettingSchema

# from utils.false_input_warning_screen import FalseInputWarning
# from utils.confirm_screen import Confirm
from ...model.spec import SpecSchema
from ..feature_widgets.features import TaskBased
from ..utils.context import ctx


class RunCLX(Widget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        #  self.top_parent = app
        #  self.ctx = ctx
        self.old_cache: defaultdict[str, defaultdict[str, dict[str, Any]]] | None = None

    #  ctx.cache = user_selections_dict

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield Pretty("", id="this_output")
            yield Button("Refresh")

    def on_button_pressed(self):
        self.dump_dict_to_contex()
        # print("uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu", ctx.cache)
        self.get_widget_by_id("this_output").update(
            json.loads(SpecSchema().dumps(ctx.spec, many=False, indent=4, sort_keys=False))
        )

    def dump_dict_to_contex(self):
        entity = "desc"
        filters = {"datatype": "ref", "suffix": "atlas"}
        filepaths = ctx.database.get(**filters)
        tagvals = ctx.database.tagvalset(entity, filepaths=filepaths)
        print("tagvalstagvalstagvalstagvals", tagvals)

        print("ccccccccccccccccccc", pd.DataFrame.from_dict(ctx.cache).index, pd.DataFrame.from_dict(ctx.cache).columns)
        #      print('fffffffffiles only', pd.DataFrame.from_dict(ctx.cache).loc['files', :].index)
        #      print('fffffffffiles only', pd.DataFrame.from_dict(ctx.cache).loc['files', :])
        #      for item in pd.DataFrame.from_dict(ctx.cache).loc['files', :].index:
        #          print(pd.DataFrame.from_dict(ctx.cache).loc['files', item])

        print("children teeeeeeeeeeeeeeeeeeeeeeeeest", self.app.walk_children(TaskBased))

        print("lets seeee this", ctx.database.filepaths_by_tags, "--------------", ctx.database.tags_by_filepaths)
        ctx.database.filepaths_by_tags: dict[str, dict[str, set[str]]] = dict()
        ctx.database.tags_by_filepaths: dict[str, dict[str, str]] = dict()
        #    for w in self.app.walk_children(TaskBased):
        #        w.refresh_event_list()
        # the cache key logic goes like this: first it is the particular name of the main item, for example a feature called
        # 'foo' will produce a key "foo" this is the "name". Second, it is the main group type of the item, if it is the
        # feature then the group type is feature, if it is for example bold file pattern then it is the bold file pattern,
        # and third are the various own items of the group type, thus these vary from group to group
        # The reason why this goes name-group type-items is that it is easier to delete the particular main item if its name
        # is at the first level
        ctx.spec.features.clear()
        ctx.spec.settings.clear()
        print("vvvvvvvvvvvvvvvvvvvvvvv", ctx.cache["bids"])
        ctx.spec.files.clear()

        print("uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu", ctx.cache)
        print("2222lets seeee this", ctx.database.filepaths_by_tags, "--------------", ctx.database.tags_by_filepaths)

        for name in ctx.cache:
            #  if name != "files":
            print("nnnnnnnnnnnnnnnnnnnnnnname", name)
            # for preprocessed image output there are no features, thus the dict is empty

            # for settings
            # settingdict: dict = {}
            # setting = {**settingdict}
            # setting = {}
            # # setting["name"] = ctx.cache[name]["settings"]["name"]
            # ctx.spec.settings.append(SettingSchema().load(setting, partial=True))
            # here it is ok, because since it is empty, there are no iterations

            ####################################################
            # if "settings" in ctx.cache[name]:
            # settingdict = ctx.cache[name]["settings"]

            # setting = {**settingdict} if settingdict is not None else {}

            # #   if self._name is not None:
            # #       assert self._name not in self.names, f"Duplicate {noun} name"
            # #       setting["name"] = self._name

            # ctx.spec.settings.append(SettingSchema().load(setting, partial=True))
            ######################################################
            #        if "features" in ctx.cache[name] or "settings" in ctx.cache[name]:

            if ctx.cache[name]["features"] != {}:
                featureobj = Feature(name=name, type=ctx.cache[name]["features"]["type"])
                ctx.spec.features.append(featureobj)
                for key in ctx.cache[name]["features"]:
                    print("wwwwwwwwwwworking on the features!!!!!!!")
                    try:
                        setattr(ctx.spec.features[-1], key, ctx.cache[name]["features"][key])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
            if ctx.cache[name]["settings"] != {}:
                ctx.spec.settings.append(SettingSchema().load({}, partial=True))
                for key in ctx.cache[name]["settings"]:
                    print("wwwwwwwwwwworking on the settings!!!!!!!")
                    try:
                        setattr(ctx.spec.settings[-1], key, ctx.cache[name]["settings"][key])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
            if ctx.cache["bids"]["files"] != {} and name == "bids":
                ctx.put(BidsFileSchema().load({"datatype": "bids", "path": ctx.cache["bids"]["files"]}))

            if ctx.cache[name]["files"] != {} and name != "bids":
                print('thissssssssss ctx.cache[name]["files"]', name, "---", ctx.cache[name]["files"])
                ctx.spec.files.append(ctx.cache[name]["files"])
                ctx.database.put(ctx.spec.files[-1])  # we've got all tags, so we can add the fileobj to the index
            self.old_cache = copy.deepcopy(ctx.cache)
        ctx.refresh_available_images()

        # print('ccccccccccccccccccccccccccccccc ctx.spec.files', [f.path for f in ctx.spec.files])
        # #try:
        # print('1111111111ccccccccccccccccccccc', ctx.database.fromspecfileobj(ctx.spec.files[-1]))
        # la =  ctx.database.fromspecfileobj(ctx.spec.files[-1])
        # if la is not None:
        # print('2222ccccccccccccccccccccccc',[f.path for f in ctx.database.fromspecfileobj(ctx.spec.files[-1])])
        # #except:
        # #   print('failed')
