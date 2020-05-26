# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from calamities import (
    TextElement,
    get_entities_in_path,
    MultiNumberInputView,
    TextInputView,
    TextView,
    SpacerView,
)

import logging
from os import path as op
from copy import deepcopy

from ..pattern import FilePatternStep
from ...spec import (
    bold_entities,
    PreprocessedBoldTagsSchema,
    File,
    EventsTagsSchema,
    Contrast,
    Variable,
)
from ..utils import BranchStep, YesNoStep, make_name_suggestion, forbidden_chars
from ..step import Step
from ...io import analysis_parse_condition_files
from ...utils import splitext
from .setting import PreSmoothingSettingStep


def _get_conditions(ctx):
    out_list = list(analysis_parse_condition_files(ctx.spec.analyses[-1], ctx.database))
    if out_list is None or len(out_list) == 0:
        return
    event_filepaths, conditions_list, onsets_list, durations_list = zip(*out_list)
    conditionssets = [set(conditions) for conditions in conditions_list]
    conditions = set.intersection(*conditionssets)
    if len(conditions) == 0:
        return
    ctx.spec.analyses[-1].variables = [
        Variable(type="events", name=condition) for condition in conditions
    ]
    return ctx.spec.analyses[-1].variables


class AddAnotherContrastStep(YesNoStep):
    header_str = "Add another contrast?"
    yes_step_type = None  # add later, because not yet defined
    no_step_type = PreSmoothingSettingStep


class ContrastValuesStep(Step):
    def _format_variable(self, variable):
        return f'"{variable}"'

    def setup(self, ctx):
        self._append_view(TextView("Specify contrast values"))
        self.varname_by_str = {
            self._format_variable(variable.name): variable.name
            for variable in ctx.spec.analyses[-1].variables
        }
        self.options = sorted(list(self.varname_by_str.keys()))
        self.input_view = MultiNumberInputView(self.options)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        valuedict = self.input_view()
        if valuedict is None:
            return False
        newdict = {varname: valuedict[dsp] for dsp, varname in self.varname_by_str.items()}
        ctx.spec.analyses[-1].contrasts[-1].values = newdict
        return True

    def next(self, ctx):
        return AddAnotherContrastStep(self.app)(ctx)


class ContrastNameStep(Step):
    def setup(self, ctx):
        if ctx.spec.analyses[-1].contrasts is None:
            self._append_view(TextView("Specify contrasts"))
            self._append_view(SpacerView(1))
            index = 1
        else:
            index = max(1, len(ctx.spec.analyses[-1].contrasts))
        if ctx.spec.analyses[-1].contrasts is None:
            ctx.spec.analyses[-1].contrasts = []
        ctx.spec.analyses[-1].contrasts.append(Contrast(type="t"))
        suggestion = make_name_suggestion("contrast", index=index)
        self._append_view(TextView("Specify contrast name"))
        self.input_view = TextInputView(text=suggestion)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            value = self.input_view()
            if value is None:
                return False
            if forbidden_chars.search(value) is None:
                ctx.spec.analyses[-1].contrasts[-1].name = value
                break
        return True

    def next(self, ctx):
        return ContrastValuesStep(self.app)(ctx)


AddAnotherContrastStep.yes_step_type = ContrastNameStep


class EventsStep(FilePatternStep):
    filetype_str = "event"
    tags_dict = {"datatype": "func", "suffix": "events"}
    allowed_entities = bold_entities
    ask_if_missing_entities = ["task"]
    required_in_pattern_entities = []
    tags_schema = EventsTagsSchema()

    def _transform_extension(self, ext):
        raise NotImplementedError

    def run(self, ctx):
        error_color = self.app.layout.color.red
        while True:
            pattern = self.file_pattern_input_view()
            if pattern is None:
                return False
            try:
                _, ext = splitext(pattern)
                if ext[0] == ".":  # remove leading dot
                    ext = ext[1:]
                analysis_obj = ctx.spec.analyses[-1]
                tags_dict = PreprocessedBoldTagsSchema().dump(analysis_obj.tags)
                entities_in_pattern = get_entities_in_path(pattern)
                tags_dict = {
                    k: v
                    for k, v in tags_dict.items()
                    if k in self.allowed_entities and k not in entities_in_pattern
                }
                tags_dict.update(self.tags_dict)
                tags_dict.update({"extension": self._transform_extension(ext)})
                tags_obj = self.tags_schema.load(tags_dict)
                file_obj = File(path=op.abspath(pattern), tags=tags_obj)
                scratchctx = deepcopy(ctx)
                scratchctx.add_file_obj(file_obj)
                variables = _get_conditions(scratchctx)
                if variables is None:
                    self.file_pattern_input_view.show_message(
                        TextElement("Failed to read files", color=error_color)
                    )
                    continue
                ctx.add_file_obj(file_obj)
                ctx.spec.analyses[-1].variables = variables
                return True
            except Exception as e:
                logging.getLogger("pipeline.ui").exception("Exception: %s", e)
                self.file_pattern_input_view.show_message(TextElement(str(e), color=error_color))

    def next(self, ctx):
        return ContrastNameStep(self.app)(ctx)


class MatEventsStep(EventsStep):
    def _transform_extension(self, ext):
        assert ext == "mat"
        return ext


class TxtEventsStep(EventsStep):
    allowed_entities = bold_entities + ["condition"]
    required_in_pattern_entities = ["condition"]

    def _transform_extension(self, ext):
        return "txt"


class TsvEventsStep(EventsStep):
    def _transform_extension(self, ext):
        return "tsv"


class EventsTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the condition/explanatory variable file type"
    options = {
        "SPM multiple conditions": MatEventsStep,
        "FSL 3-column": TxtEventsStep,
        "BIDS TSV": TsvEventsStep,
    }

    def setup(self, ctx):
        self.is_first_run = True
        self.is_missing = False
        cond = _get_conditions(ctx)
        if cond is None or len(cond) == 0:
            self.is_missing = True
            super(EventsTypeStep, self).setup(ctx)

    def run(self, ctx):
        if self.is_missing:
            return super(EventsTypeStep, self).run(ctx)
        return self.is_first_run

    def next(self, ctx):
        if self.is_missing:
            return super(EventsTypeStep, self).next(ctx)
        else:
            if self.is_first_run:
                self.is_first_run = False
                return ContrastNameStep(self.app)(ctx)
            else:
                return


TaskBasedStep = EventsTypeStep
