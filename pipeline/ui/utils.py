# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import (
    TextView,
    SpacerView,
    SingleChoiceInputView,
    NumberInputView,
    MultiNumberInputView,
    TextElement,
    TextElementCollection,
)

import re

import inflect
from inflection import humanize, parameterize, underscore, camelize
import numpy as np

from .step import Step
from ..spec import entity_colors

p = inflect.engine()

forbidden_chars = re.compile(r"[^a-zA-Z0-9_-]")
_check_tagval = re.compile(r"[a-zA-Z0-9_-]+")


def make_name_suggestion(*words, index=None):
    suggestion = " ".join(words)
    if index is not None:
        ordinal = p.number_to_words(p.ordinal(index))
        suggestion = f"{ordinal} {suggestion}"
    suggestion = camelize(underscore(parameterize(suggestion)))
    suggestion = forbidden_chars.sub("", suggestion)
    return suggestion


def messagefun(database, filetype, filepaths, tagnames):
    message = ""
    if filepaths is not None:
        message = p.inflect(f"Found {len(filepaths)} {filetype} plural('file', {len(filepaths)})")
        if len(filepaths) > 0:
            n_by_tag = dict()
            for tagname in tagnames:
                tagvalset = database.get_tagval_set(tagname, filepaths=filepaths)
                if tagvalset is not None:
                    n_by_tag[tagname] = len(tagvalset)
            tagmessages = [
                p.inflect(f"{n} plural('{tagname}', {n})")
                for tagname, n in n_by_tag.items()
                if n > 0
            ]
            message += " "
            message += "for"
            message += " "
            message += p.join(tagmessages)
    return message


class BranchStep(Step):
    def setup(self, ctx):
        if hasattr(self, "header_str") and self.header_str is not None:
            self._append_view(TextView(self.header_str))
        self.input_view = SingleChoiceInputView(
            list(self.options.keys()), isVertical=self.is_vertical
        )
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        return True

    def next(self, ctx):
        if self.choice is None:
            return
        elif self.options[self.choice] is None:
            return ctx
        else:
            return self.options[self.choice](self.app)(ctx)


class YesNoStep(BranchStep):
    is_vertical = False

    def __init__(self, app):
        super(YesNoStep, self).__init__(app)
        self.options = {"Yes": self.yes_step_type, "No": self.no_step_type}


class NumericMetadataStep(Step):
    min = -np.inf
    max = np.inf
    initial_value = 0

    def setup(self, ctx):
        file_obj = ctx.spec.files[-1]
        self.tags_obj = file_obj.tags
        assert hasattr(self.tags_obj, self.entity)
        self._append_view(TextView(self.header_str))
        self.number_input_view = NumberInputView(self.initial_value, min=self.min, max=self.max)
        self._append_view(self.number_input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        number = self.number_input_view()
        if number is None:  # was cancelled
            return False
        setattr(self.tags_obj, self.entity, number)
        return True

    def next(self, ctx):
        return self.next_step_type(self.app)(ctx)


class MultiNumericMetadataStep(Step):
    min = -np.inf
    max = np.inf
    initial_value = 0

    def setup(self, ctx):
        file_obj = ctx.spec.files[-1]
        self.tags_obj = file_obj.tags
        for entity in self.entities_by_str.values():
            assert hasattr(self.tags_obj, entity)
        self._append_view(TextView(self.header_str))
        self.multi_number_input_view = MultiNumberInputView(
            list(self.entities_by_str.keys()),
            initial_values=[self.initial_value] * len(self.entities_by_str),
            min=self.min,
            max=self.max,
        )
        self._append_view(self.multi_number_input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        numbers_by_str = self.multi_number_input_view()
        if numbers_by_str is None:  # was cancelled
            return False
        for str, entity in self.entities_by_str.items():
            setattr(self.tags_obj, entity, numbers_by_str[str])
        return True

    def next(self, ctx):
        return self.next_step_type(self.app)(ctx)


class BaseBOLDSelectStep(Step):
    def _format_entity(self, entity):
        return humanize(entity)

    def _format_tag(self, tag):
        return f'"{tag}"'

    def _tokenize_entity(self, entity):
        entity_str = self._format_entity(entity)
        return TextElement(entity_str, color=entity_colors[entity])

    def _make_table_row(self, columns, colwidths, color_obj, offset=0, color_list=None):
        row_elements = []
        if offset > 0:
            space = TextElement(" " * offset, color=color_obj.default)
            row_elements.append(space)
        for i, text in enumerate(columns):
            text = text
            n = colwidths[i] - len(text)
            if i > 0:
                n += 1
            if color_list is not None:
                element = TextElement(text, color=color_list[i],)
            else:
                element = TextElement(text,)
            space = TextElement(" " * n, color=color_obj.default)
            row_elements.append(element)
            row_elements.append(space)
        return TextElementCollection(row_elements)

    def _setup_options(self, ctx, filepaths, header_nchr_prepend=0):
        color_obj = self.app.layout.color
        self.entities, self.tags_set = ctx.database.get_multi_tagval_set(
            self.entities, filepaths=filepaths
        )
        colwidths = [
            max(
                len(self._format_entity(entity)),
                max(len(self._format_tag(tagval)) for tagval in tagvals),
            )
            for entity, tagvals in zip(self.entities, zip(*self.tags_set))
        ]
        entity_strs = [self._format_entity(entity) for entity in self.entities]
        entity_colors_list = [entity_colors[entity] for entity in self.entities]
        self._append_view(
            TextView(
                self._make_table_row(
                    entity_strs,
                    colwidths,
                    color_obj,
                    offset=header_nchr_prepend,
                    color_list=entity_colors_list,
                )
            )
        )
        options = []
        self.tags_by_str = {}
        for tags in self.tags_set:
            option = self._make_table_row(
                [self._format_tag(tag) for tag in tags], colwidths, color_obj
            )
            self.tags_by_str[str(option)] = tags
            options.append(option)
        return options
