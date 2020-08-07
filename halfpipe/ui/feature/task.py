# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from calamities import (
    MultiNumberInputView,
    TextInputView,
    TextView,
    SpacerView,
    MultipleChoiceInputView,
    MultiCombinedNumberAndSingleChoiceInputView
)

from ..step import Step, BranchStep, YesNoStep
from ..pattern import FilePatternStep
from ..metadata import CheckMetadataStep
from ..utils import forbidden_chars
from ...utils import first, ravel
from ..setting import get_setting_init_steps
from .loop import SettingValsStep

from ...io import find_and_parse_condition_files
from ...model import TxtEventsFileSchema, TsvEventsFileSchema, MatEventsFileSchema, TContrastSchema

next_step_type = SettingValsStep


def _format_variable(variable):
    return f'"{variable}"'


def _get_conditions(ctx):
    out_list = list(find_and_parse_condition_files(ctx.database, filters=ctx.spec.settings[-1].get("filters")))
    if out_list is None or len(out_list) == 0:
        return

    event_filepaths, conditions_list, onsets_list, durations_list = zip(*out_list)

    conditionssets = [set(conditions) for conditions in conditions_list]
    conditions = set.intersection(*conditionssets)

    if len(conditions) == 0:
        return

    ordered_conditions = []
    for c in ravel(conditions_list):
        if c in conditions and c not in ordered_conditions:
            ordered_conditions.append(c)

    ctx.spec.features[-1].conditions = ordered_conditions


class AddAnotherContrastStep(YesNoStep):
    header_str = "Add another contrast?"
    yes_step_type = None  # add later, because not yet defined
    no_step_type = next_step_type


class ConfirmInconsistentStep(YesNoStep):
    no_step_type = None

    def __init__(self, app, noun, next_step_type):
        self.header_str = f"Do you really want to use inconsistent {noun} across features?"
        self.yes_step_type = next_step_type
        super(ConfirmInconsistentStep, self).__init__(app)

    def run(self, ctx):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        if self.choice == "No":
            return False
        return True


class HighPassFilterCutoffStep(Step):
    noun = "temporal filter"
    display_strs = ["High-pass width in seconds"]
    suggestion = (125.0,)

    def setup(self, ctx):
        self.result = None

        self._append_view(TextView(f"Apply a {self.noun} to the design matrix?"))

        self.valset = set()

        for feature in ctx.spec.features:
            if hasattr(feature, "high_pass_filter_cutoff"):
                self.valset.add(feature.high_pass_filter_cutoff)

        suggestion = self.suggestion
        if len(self.valset) > 0:
            suggestion = (first(self.valset),)

        self.input_view = MultiCombinedNumberAndSingleChoiceInputView(
            self.display_strs, ["Skip"], initial_values=suggestion
        )

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        if self.result is not None:
            ctx.spec.features[-1].high_pass_filter_cutoff = first(self.result.values())  # only one value

        next_step_type = AddAnotherContrastStep

        if len(self.valset) == 1 and self.result not in self.valset:
            return ConfirmInconsistentStep(self.app, f"{self.noun} values", next_step_type)(ctx)

        return next_step_type(self.app)(ctx)


class ContrastValuesStep(Step):
    def setup(self, ctx):
        self.result = None

        if (
            not hasattr(ctx.spec.features[-1], "conditions")
            or ctx.spec.features[-1].conditions is None
            or len(ctx.spec.features[-1].conditions) == 0
        ):
            raise ValueError("Conditions not found")

        self._append_view(TextView("Specify contrast values"))

        conditions = ctx.spec.features[-1].conditions
        self.options = [_format_variable(condition) for condition in conditions]
        self.varname_by_str = dict(zip(self.options, conditions))

        self.input_view = MultiNumberInputView(self.options)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        if self.result is not None:
            newdict = {varname: self.result[dsp] for dsp, varname in self.varname_by_str.items()}
            ctx.spec.features[-1].contrasts[-1]["values"] = newdict

        return AddAnotherContrastStep(self.app)(ctx)


class ContrastNameStep(Step):
    def setup(self, ctx):
        if (
            not hasattr(ctx.spec.features[-1], "contrasts")
            or ctx.spec.features[-1].contrasts is None
        ):
            ctx.spec.features[-1].contrasts = []

        if len(ctx.spec.features[-1].contrasts) == 0:
            self._append_view(TextView("Specify contrasts"))
            self._append_view(SpacerView(1))

        self.names = set(contrast.get("name") for contrast in ctx.spec.features[-1].contrasts)

        base = "contrast"
        index = 1
        suggestion = f"{base}{index}"
        while suggestion in self.names:
            suggestion = f"{base}{index}"
            index += 1

        self._append_view(TextView("Specify contrast name"))

        self.input_view = TextInputView(
            text=suggestion, isokfun=lambda text: forbidden_chars.search(text) is None
        )

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        assert self.result not in self.names, "Duplicate contrast name"

        contrast = TContrastSchema().load({"name": self.result})
        ctx.spec.features[-1].contrasts.append(contrast)

        return ContrastValuesStep(self.app)(ctx)


AddAnotherContrastStep.yes_step_type = ContrastNameStep


class ConditionsSelectStep(Step):
    def setup(self, ctx):
        self.result = None

        if (
            not hasattr(ctx.spec.features[-1], "conditions")
            or ctx.spec.features[-1].conditions is None
            or len(ctx.spec.features[-1].conditions) == 0
        ):
            _get_conditions(ctx)

        self._append_view(TextView("Select conditions to add to the model"))

        conditions = ctx.spec.features[-1].conditions
        self.options = [_format_variable(condition) for condition in conditions]
        self.str_by_varname = dict(zip(conditions, self.options))

        self.input_view = MultipleChoiceInputView(self.options, checked=[*self.options])

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        if self.result is not None:
            conditions = []
            for condition in ctx.spec.features[-1].conditions:
                is_selected = self.result[self.str_by_varname[condition]]
                if is_selected:
                    conditions.append(condition)
            ctx.spec.features[-1].conditions = conditions

        return ContrastNameStep(self.app)(ctx)


class CheckUnitsStep(CheckMetadataStep):
    schema = MatEventsFileSchema

    key = "units"

    next_step_type = ConditionsSelectStep


class EventsStep(FilePatternStep):
    header_str = "Specify event data"

    filetype_str = "event"
    filedict = {"datatype": "func", "suffix": "events"}

    ask_if_missing_entities = []
    required_in_path_entities = []

    next_step_type = ConditionsSelectStep

    def _transform_extension(self, ext):
        raise NotImplementedError()


class MatEventsStep(EventsStep):
    schema = MatEventsFileSchema

    next_step_type = CheckUnitsStep

    def _transform_extension(self, ext):
        assert ext == ".mat"
        return ext


class TxtEventsStep(EventsStep):
    schema = TxtEventsFileSchema

    required_in_path_entities = ["condition"]

    def _transform_extension(self, ext):
        return ".txt"


class TsvEventsStep(EventsStep):
    schema = TsvEventsFileSchema

    def _transform_extension(self, ext):
        return ".tsv"


class EventsTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the event file type"
    options = {
        "SPM multiple conditions": MatEventsStep,
        "FSL 3-column": TxtEventsStep,
        "BIDS TSV": TsvEventsStep,
    }

    def setup(self, ctx):
        self.is_first_run = True
        self.should_run = False

        if (
            not hasattr(ctx.spec.features[-1], "conditions")
            or ctx.spec.features[-1].conditions is None
            or len(ctx.spec.features[-1].conditions) == 0
        ):
            _get_conditions(ctx)

        if (
            not hasattr(ctx.spec.features[-1], "conditions")
            or ctx.spec.features[-1].conditions is None
            or len(ctx.spec.features[-1].conditions) == 0
        ):
            self.should_run = True
            super(EventsTypeStep, self).setup(ctx)

    def run(self, ctx):
        if self.should_run:
            return super(EventsTypeStep, self).run(ctx)
        return self.is_first_run

    def next(self, ctx):
        if self.should_run:
            return super(EventsTypeStep, self).next(ctx)
        else:
            if self.is_first_run:
                self.is_first_run = False
                return ConditionsSelectStep(self.app)(ctx)
            else:
                return


TaskBasedSettingInitStep = get_setting_init_steps(
    EventsTypeStep,
    settingdict={"bandpass_filter": {"type": "gaussian"}, "grand_mean_scaling": {"mean": 10000.0}},
)


TaskBasedStep = TaskBasedSettingInitStep
