# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import cast

from inflection import humanize, underscore

from ...model.filter import FilterSchema
from ...model.setting import SettingSchema
from ...model.tags import entities
from ...utils.format import format_like_bids
from ..components import (
    MultiMultipleChoiceInputView,
    SpacerView,
    TextElement,
    TextInputView,
    TextView,
)
from ..pattern import entity_display_aliases
from ..step import Step
from ..utils import entity_colors, forbidden_chars


def feature_namefun(ctx):
    featurename = underscore(ctx.spec.features[-1].name)
    name = format_like_bids(f"{featurename} setting")
    ctx.spec.features[-1].setting = name
    return name


def get_setting_init_steps(next_step_type, settingdict: dict | None = None, namefun=feature_namefun, noun="setting"):
    settingdict = {} if settingdict is None else settingdict

    class SettingFilterStep(Step):
        def _format_tag(self, tag):
            return f'"{tag}"'

        def setup(self, ctx):
            self.is_first_run = True
            self.choice = None

            bold_filedict = {"datatype": "func", "suffix": "bold"}
            filepaths = ctx.database.get(**bold_filedict)
            self.filepaths = list(filepaths)
            assert len(self.filepaths) > 0

            db_entities, db_tags_set = ctx.database.multitagvalset(entities, filepaths=self.filepaths)

            self.entities = []
            options = []
            self.tagval_by_str = {}
            values = []
            for entity, tagvals_list in zip(db_entities, zip(*db_tags_set, strict=False), strict=False):
                if entity == "sub":
                    continue

                tagvals_set = set(tagvals_list)
                if 1 < len(tagvals_set) < 16:
                    self.entities.append(entity)

                    entity_str = entity
                    if entity_str in entity_display_aliases:
                        entity_str = entity_display_aliases[entity_str]
                    entity_str = humanize(entity_str)
                    options.append(TextElement(entity_str, color=entity_colors[entity]))

                    if None in tagvals_set:
                        tagvals_set.remove(None)

                    tagvals = sorted(list(tagvals_set))

                    row = [f'"{tagval}"' for tagval in tagvals]
                    values.append(row)

                    self.tagval_by_str.update(dict(zip(row, tagvals, strict=False)))

            if len(options) == 0:
                self.should_run = False
            else:
                self.should_run = True
                self._append_view(TextView("Specify images to use"))

                self.input_view = MultiMultipleChoiceInputView(options, values, checked=values)

                self._append_view(self.input_view)
                self._append_view(SpacerView(1))

        def run(self, _):
            if not self.should_run:
                return self.is_first_run
            else:
                self.choice = self.input_view()
                if self.choice is None:
                    return False
                return True

        def next(self, ctx):
            if self.choice is not None:
                filter_schema = FilterSchema()

                if ctx.spec.settings[-1].get("filters") is None:
                    ctx.spec.settings[-1]["filters"] = []

                for entity, checked in zip(self.entities, self.choice, strict=False):
                    if all(checked.values()):
                        continue

                    assert any(checked.values())

                    selected_tagvals = []
                    for tag_str, is_selected in checked.items():
                        if is_selected:
                            selected_tagvals.append(self.tagval_by_str[tag_str])
                    filter = filter_schema.load(
                        {
                            "type": "tag",
                            "action": "include",
                            "entity": entity,
                            "values": selected_tagvals,
                        }
                    )
                    ctx.spec.settings[-1]["filters"].append(filter)

            if self.should_run or self.is_first_run:
                self.is_first_run = False
                return next_step_type(self.app)(ctx)

    class SettingNameStep(Step):
        header_str = f"Specify {noun} name"

        def setup(self, ctx):
            self._name = None
            self.is_first_run = True
            self.should_run = False

            assert ctx.spec.settings is not None
            self.names = set(setting["name"] for setting in ctx.spec.settings)

            if "name" in cast(dict, settingdict):
                pass
            elif namefun is not None:
                self._name = namefun(ctx)
            else:
                self.should_run = True

                self._append_view(TextView(self.header_str))

                base = "preproc"
                suggestion = base
                index = 1
                while suggestion in self.names:
                    suggestion = f"{base}{index}"
                    index += 1

                self.input_view = TextInputView(
                    text=suggestion,
                    isokfun=lambda text: forbidden_chars.search(text) is None,
                )

                self._append_view(self.input_view)
                self._append_view(SpacerView(1))

        def run(self, _):
            if not self.should_run:
                return self.is_first_run
            else:
                self._name = self.input_view()
                if self._name is None:
                    return False
                return True

        def next(self, ctx):
            setting = {**settingdict} if settingdict is not None else {}

            if self._name is not None:
                assert self._name not in self.names, f"Duplicate {noun} name"
                setting["name"] = self._name

            ctx.spec.settings.append(SettingSchema().load(setting, partial=True))

            if self.is_first_run or self.should_run:
                self.is_first_run = False
                return SettingFilterStep(self.app)(ctx)

    return SettingNameStep
