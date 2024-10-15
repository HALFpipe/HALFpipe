# -*- coding: utf-8 -*-
# ok (more-less) to review

import copy
import json
import sys
import traceback
from collections import defaultdict
from typing import Any

from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Pretty

from ...model.feature import Feature
from ...model.file.bids import BidsFileSchema
from ...model.setting import SettingSchema
from ...model.spec import SpecSchema
from ...utils.copy import deepcopy
from ..utils.context import ctx


class RunCLX(Widget):
    """
    RunCLX Class

    This class is responsible for managing the user interface that handles refreshing the data and updating the context
    based on user interactions.

    Attributes
    ----------
    old_cache : defaultdict or None
        A cache of old data, structured as a defaultdict of defaultdicts containing dictionaries.

    Methods
    -------
    __init__(**kwargs)
        Initializes the RunCLX class with only textual widget attributes.

    compose() -> ComposeResult
        Composes the UI by adding a ScrollableContainer with an output area and a refresh button.

    on_button_pressed()
        Handles the event when the refresh button is pressed. Dumps the current cache to the context
        and updates the output widget with the refreshed data.

    dump_dict_to_contex()
        Converts the cached data to the context format:
            1. Clears the existing data in the context.
            2. Iterates over the cache and fills the context with features, settings, and files.
            3. Handles specific cases for BIDS and non-BIDS files.
            4. Deep copies the current cache to old_cache.
            5. Refreshes available images in the context.
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.old_cache: defaultdict[str, defaultdict[str, dict[str, Any]]] | None = None

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
        # the cache key logic goes like this: first it is the particular name of the main item, for example a feature called
        # 'foo' will produce a key "foo" this is the "name". Second, it is the main group type of the item, if it is the
        # feature then the group type is feature, if it is for example bold file pattern then it is the bold file pattern,
        # and third are the various own items of the group type, thus these vary from group to group
        # The reason why this goes name-group type-items is that it is easier to delete the particular main item if its name
        # is at the first level

        # clear the whole database and all other entries in the context object
        ctx.database.filepaths_by_tags = dict()
        ctx.database.tags_by_filepaths = dict()
        ctx.spec.features.clear()
        ctx.spec.settings.clear()
        ctx.spec.files.clear()

        # iterate now over the whole cache and fill the context object
        # the "name" is widget name carying the particular user choices, either a feature or file pattern
        for name in ctx.cache:
            if ctx.cache[name]["features"] != {}:
                featureobj = Feature(name=name, type=ctx.cache[name]["features"]["type"])
                ctx.spec.features.append(featureobj)
                for key in ctx.cache[name]["features"]:
                    try:
                        setattr(ctx.spec.features[-1], key, ctx.cache[name]["features"][key])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
            if ctx.cache[name]["settings"] != {}:
                ctx.spec.settings.append(SettingSchema().load({}, partial=True))
                for key in ctx.cache[name]["settings"]:
                    try:
                        setattr(ctx.spec.settings[-1], key, ctx.cache[name]["settings"][key])
                        # if there are no filters, than put there just empty list
                        if key == "filters":
                            if ctx.cache[name]["settings"][key][0]["values"] == []:
                                setattr(ctx.spec.settings[-1], key, [])
                    except Exception:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print(f"An exception occurred: {exc_value}")
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                # this is for the case of falff
                if "unfiltered_setting" in ctx.cache[name]:
                    unfiltered_setting = deepcopy(ctx.spec.settings[-1])
                    unfiltered_setting["name"] = ctx.cache[name]["unfiltered_setting"]["name"]
                    unfiltered_setting["bandpass_filter"] = None  # remove bandpass filter, keep everything else
                    ctx.spec.settings.append(unfiltered_setting)

            if ctx.cache["bids"]["files"] != {} and name == "bids":
                ctx.put(BidsFileSchema().load({"datatype": "bids", "path": ctx.cache["bids"]["files"]}))

            if ctx.cache[name]["files"] != {} and name != "bids":
                ctx.spec.files.append(ctx.cache[name]["files"])
                ctx.database.put(ctx.spec.files[-1])  # we've got all tags, so we can add the fileobj to the index
            self.old_cache = copy.deepcopy(ctx.cache)
        # refresh at the end available images
        ctx.refresh_available_images()
