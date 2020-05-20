# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import (
    TextView,
    SpacerView,
    FilePatternInputView,
    TextInputView,
    get_entities_in_path,
    TextElement,
)

import re
from os import path as op
import logging
from copy import deepcopy

from .step import Step
from ..spec import File, entity_colors
from .utils import messagefun, forbidden_chars
from ..utils import splitext

_check_tagval = re.compile(r"[a-zA-Z0-9_-]+")


class FilePatternSummaryStep(Step):
    def setup(self, ctx):
        filepaths = ctx.database.get(**self.tags_dict)
        self.is_first_run = True
        message = messagefun(ctx.database, self.filetype_str, filepaths, self.allowed_entities,)
        self._append_view(TextView(message))
        self._append_view(SpacerView(1))

    def run(self, ctx):
        return self.is_first_run

    def next(self, ctx):
        if self.is_first_run:
            self.is_first_run = False
            return self.next_step_type(self.app)(ctx)
        else:
            return


class FilePatternStep(Step):
    header_str = None
    suggest_file_stem = False

    def setup(self, ctx):
        self.file_obj = None
        if self.header_str is not None:
            self._append_view(TextView(self.header_str))
            self._append_view(SpacerView(1))
        self._append_view(TextView(f"Specify the path of the {self.filetype_str} files"))
        required_entities = self.ask_if_missing_entities + self.required_in_pattern_entities
        entity_instruction_strs = []
        for entity in required_entities:
            entity_str = entity.replace("_", " ")
            entity_instruction_strs.append(f"Put {{{entity}}} in place of the {entity_str} names")
        for entity in self.allowed_entities:
            if entity not in required_entities:
                entity_str = entity.replace("_", " ")
                entity_instruction_strs.append(
                    f"Put {{{entity}}} in place of the {entity_str} names if applicable"
                )
        entity_instruction_views = [TextView("") for str in entity_instruction_strs]
        for view in entity_instruction_views:
            self._append_view(view)
        entity_colors_list = [entity_colors[entity] for entity in self.allowed_entities]
        self.file_pattern_input_view = FilePatternInputView(
            self.allowed_entities,
            entity_colors_list=entity_colors_list,
            required_entities=self.required_in_pattern_entities,
        )
        self._append_view(self.file_pattern_input_view)
        for str, view in zip(entity_instruction_strs, entity_instruction_views):
            view.text = self.file_pattern_input_view._tokenize(str, addBrackets=False)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            pattern = self.file_pattern_input_view()
            if pattern is None:
                return False
            try:
                _, ext = splitext(pattern)
                if ext[0] == ".":  # remove leading dot
                    ext = ext[1:]
                tags_dict = {"extension": ext}
                tags_dict.update(self.tags_dict)
                tags_obj = self.tags_schema.load(tags_dict)
                self.file_obj = File(path=op.abspath(pattern), tags=tags_obj)
                return True
            except Exception as e:
                logging.getLogger("pipeline.ui").exception("Exception: %s", e)
                error_color = self.app.layout.color.red
                self.file_pattern_input_view.show_message(TextElement(str(e), color=error_color))
                if ctx.debug:
                    raise

    def next(self, ctx):
        return AskForMissingEntities(
            self.app,
            self.file_obj,
            self.ask_if_missing_entities.copy(),
            self.next_step_type,
            suggest_file_stem=self.suggest_file_stem,
        )(ctx)


class AskForMissingEntities(Step):
    def __init__(
        self, app, file_obj, ask_if_missing_entities, next_step_type, suggest_file_stem=False
    ):
        super(AskForMissingEntities, self).__init__(app)
        self.file_obj = file_obj
        self.ask_if_missing_entities = ask_if_missing_entities
        self.next_step_type = next_step_type
        self.cur_entity = None
        self.suggest_file_stem = suggest_file_stem
        self.tagval = None

    def _isok(self, text):
        return _check_tagval.fullmatch(text) is not None

    def setup(self, ctx):
        self.is_first_run = True
        entites_in_path = get_entities_in_path(self.file_obj.path)
        self.tags_obj = self.file_obj.tags
        while len(self.ask_if_missing_entities) > 0:
            entity = self.ask_if_missing_entities.pop(0)
            if (
                hasattr(self.tags_obj, entity)
                and getattr(self.tags_obj, entity) is None
                and entity not in entites_in_path
            ):
                self.cur_entity = entity
                break
        if self.cur_entity is not None:
            self._append_view(TextView(f"No {self.cur_entity} name was specified"))
            self._append_view(TextView(f"Specify the {self.cur_entity} name"))
            suggestion = ""
            if self.suggest_file_stem:
                suggestion, _ = splitext(self.file_obj.path)
            self.tagval_input_view = TextInputView(text=suggestion, isokfun=self._isok)
            self._append_view(self.tagval_input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if self.cur_entity is not None:
            while True:
                self.tagval = self.tagval_input_view()
                if self.tagval is None:
                    return False
                if forbidden_chars.search(self.tagval) is None:
                    break
            return True
        return self.is_first_run

    def next(self, ctx):
        file_obj = deepcopy(self.file_obj)
        if self.tagval is not None:
            setattr(file_obj.tags, self.cur_entity, self.tagval)
        if self.cur_entity is not None or self.is_first_run:
            self.is_first_run = False
            if len(self.ask_if_missing_entities) > 0:
                return AskForMissingEntities(
                    self.app,
                    file_obj,
                    self.ask_if_missing_entities.copy(),
                    self.next_step,
                    suggest_file_stem=self.suggest_file_stem,
                )(ctx)
            else:
                ctx.add_file_obj(file_obj)
                return self.next_step_type(self.app)(ctx)
        return
