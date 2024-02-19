# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import abstractmethod
from typing import List, Optional, Type

from ...collect.events import collect_events
from ...ingest.events import ConditionFile
from ...ingest.glob import get_entities_in_path
from ...model.contrast import TContrastSchema
from ...model.feature import Feature
from ...model.file.base import File
from ...model.file.func import (
    MatEventsFileSchema,
    TsvEventsFileSchema,
    TxtEventsFileSchema,
)
from ..components import (
    CombinedMultipleAndSingleChoiceInputView,
    MultiCombinedNumberAndSingleChoiceInputView,
    MultiNumberInputView,
    SpacerView,
    TextInputView,
    TextView,
)
from ..components.input.choice import SingleChoiceInputView
from ..metadata import CheckMetadataStep
from ..pattern import FilePatternStep
from ..setting import get_setting_init_steps
from ..step import BranchStep, Context, Step, YesNoStep
from ..utils import forbidden_chars
from .loop import SettingValsStep

next_step_type: Type[Step] = SettingValsStep


def format_variable(variable):
    return f'"{variable}"'


def find_bold_file_paths(ctx):
    bold_file_paths = ctx.database.get(datatype="func", suffix="bold")

    if bold_file_paths is None:
        raise ValueError("No BOLD files in database")

    filters = ctx.spec.settings[-1].get("filters")
    bold_file_paths = set(bold_file_paths)

    if filters is not None:
        bold_file_paths = ctx.database.applyfilters(bold_file_paths, filters)

    return bold_file_paths


def get_conditions(ctx):
    bold_file_paths = find_bold_file_paths(ctx)

    conditions: list[str] = list()
    seen = set()
    for bold_file_path in bold_file_paths:
        event_file_paths = collect_events(ctx.database, bold_file_path)

        if event_file_paths is None:
            continue

        if event_file_paths in seen:
            continue

        cf = ConditionFile(data=event_file_paths)
        for condition in cf.conditions:  # maintain order
            if condition not in conditions:
                conditions.append(condition)

        seen.add(event_file_paths)

    ctx.spec.features[-1].conditions = conditions


class ConfirmInconsistentStep(YesNoStep):
    no_step_type = None

    def __init__(self, app, noun, this_next_step_type: Type[Step]):
        self.header_str = f"Do you really want to use inconsistent {noun} across features?"
        self.yes_step_type = this_next_step_type
        super(ConfirmInconsistentStep, self).__init__(app)

    def run(self, _):
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

        for feature in ctx.spec.features[:-1]:
            if feature.type == "task_based":
                if hasattr(feature, "high_pass_filter_cutoff"):
                    self.valset.add(feature.high_pass_filter_cutoff)
                else:
                    self.valset.add("Skip")

        suggestion = self.suggestion
        if len(self.valset) > 0:
            suggestion = (next(iter(self.valset)),)

        self.input_view = MultiCombinedNumberAndSingleChoiceInputView(self.display_strs, ["Skip"], initial_values=suggestion)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        value = None
        if self.result is not None:
            value = next(iter(self.result.values()))
            if isinstance(value, float):
                ctx.spec.features[-1].high_pass_filter_cutoff = value
            elif value == "Skip":
                ctx.spec.features[-1].high_pass_filter_cutoff = None
            else:
                raise ValueError(f'Unknown high_pass_filter_cutoff value "{value}"')

        this_next_step_type = next_step_type

        if len(self.valset) == 1 and value not in self.valset:
            return ConfirmInconsistentStep(self.app, f"{self.noun} values", this_next_step_type)(ctx)

        return this_next_step_type(self.app)(ctx)


class AddAnotherContrastStep(YesNoStep):
    header_str = "Add another contrast?"
    no_step_type = HighPassFilterCutoffStep


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
        self.options = [format_variable(condition) for condition in conditions]
        self.varname_by_str = dict(zip(self.options, conditions, strict=False))

        self.input_view = MultiNumberInputView(self.options)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
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
        if not hasattr(ctx.spec.features[-1], "contrasts") or ctx.spec.features[-1].contrasts is None:
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

        self.input_view = TextInputView(text=suggestion, isokfun=lambda text: forbidden_chars.search(text) is None)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
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


def get_matching_features(ctx):
    current_conditions = frozenset(ctx.spec.features[-1].conditions)

    for feature in ctx.spec.features[:-1]:
        conditions = frozenset(feature.conditions)

        if conditions.issuperset(current_conditions):
            yield feature


class CopyContrastsStep(Step):
    skip_option = "Specify manually"

    def setup(self, ctx):
        self.is_first_run: bool = True

        self.features = list(get_matching_features(ctx))
        self.should_run: bool = len(self.features) > 0

        self.choice: Optional[str] = None

        if self.should_run:
            self._append_view(TextView("Use contrasts from existing feature?"))
            options = [feature.name for feature in self.features] + [self.skip_option]
            self.input_view = SingleChoiceInputView(options, is_vertical=True)
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

    def _copy_contrasts(self, ctx):
        if not hasattr(ctx.spec.features[-1], "contrasts") or ctx.spec.features[-1].contrasts is None:
            ctx.spec.features[-1].contrasts = []

        assert self.choice is not None

        source_feature: Optional[Feature] = None
        for feature in self.features:
            if feature.name == self.choice:
                source_feature = feature

        assert source_feature is not None
        assert isinstance(source_feature.contrasts, list)

        for contrast in source_feature.contrasts:
            new_values = {k: v for k, v in contrast["values"].items() if k in ctx.spec.features[-1].conditions}

            new_contrast = dict(name=contrast["name"], values=new_values)

            contrast = TContrastSchema().load(new_contrast)
            ctx.spec.features[-1].contrasts.append(contrast)

    def next(self, ctx):
        if self.is_first_run is True or self.should_run is True:
            self.is_first_run = False

            if self.choice == self.skip_option or self.should_run is False:
                return ContrastNameStep(self.app)(ctx)

            elif self.choice is not None:
                self._copy_contrasts(ctx)

            return AddAnotherContrastStep(self.app)(ctx)


class ConditionsSelectStep(Step):
    add_file_str = "Load another event file"

    def setup(self, ctx):
        self.result = None

        get_conditions(ctx)

        self._append_view(TextView("Select conditions to add to the model"))

        conditions = ctx.spec.features[-1].conditions
        assert len(conditions) > 0, "No conditions found"
        self.options = [format_variable(condition) for condition in conditions]
        self.str_by_varname = dict(zip(conditions, self.options, strict=False))

        self.input_view = CombinedMultipleAndSingleChoiceInputView(
            self.options,
            [self.add_file_str],
            checked=[*self.options],
            is_vertical=True,
        )

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        if self.result is not None:
            if isinstance(self.result, dict):
                conditions = []
                for condition in ctx.spec.features[-1].conditions:
                    is_selected = self.result[self.str_by_varname[condition]]
                    if is_selected:
                        conditions.append(condition)
                ctx.spec.features[-1].conditions = conditions
            elif self.result == self.add_file_str:
                return EventsTypeStep(self.app, force_run=True)(ctx)
            else:
                raise ValueError()

        return CopyContrastsStep(self.app)(ctx)


class CheckUnitsStep(CheckMetadataStep):
    schema = MatEventsFileSchema

    key = "units"

    next_step_type = ConditionsSelectStep

    show_summary = False


class EventsStep(FilePatternStep):
    header_str = "Specify event data"

    filetype_str = "event"
    filedict = {"datatype": "func", "suffix": "events"}

    ask_if_missing_entities: List[str] = list()
    required_in_path_entities: List[str] = list()

    next_step_type: Type[Step] = ConditionsSelectStep

    def setup(self, ctx: Context):
        bold_file_paths = find_bold_file_paths(ctx)

        taskset = ctx.database.tagvalset("task", filepaths=bold_file_paths)
        if taskset is None:
            taskset = set()
        self.taskset = taskset

        if len(self.taskset) > 1:
            self.required_in_path_entities = ["task"]
        super(EventsStep, self).setup(ctx)

    def next(self, ctx):
        if len(self.taskset) == 1:
            assert isinstance(self.fileobj, File)
            if self.fileobj.tags.get("task") is None:
                if "task" not in get_entities_in_path(self.fileobj.path):
                    (self.fileobj.tags["task"],) = self.taskset
        return super(EventsStep, self).next(ctx)

    @abstractmethod
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

    def _transform_extension(self, _):
        return ".txt"


class TsvEventsStep(EventsStep):
    schema = TsvEventsFileSchema

    def _transform_extension(self, _):
        return ".tsv"


class EventsTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the event file type"
    options = {
        "SPM multiple conditions": MatEventsStep,
        "FSL 3-column": TxtEventsStep,
        "BIDS TSV": TsvEventsStep,
    }

    def __init__(self, app, force_run: bool = False):
        super(EventsTypeStep, self).__init__(app)
        self.force_run = force_run

    def setup(self, ctx):
        self.is_first_run = True
        self.should_run = False

        # try to load conditions if not available
        get_conditions(ctx)

        if (
            not hasattr(ctx.spec.features[-1], "conditions")
            or ctx.spec.features[-1].conditions is None
            or len(ctx.spec.features[-1].conditions) == 0
            or self.force_run
        ):  # check if load was successful
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
    settingdict={
        "bandpass_filter": {"type": "gaussian"},
        "grand_mean_scaling": {"mean": 10000.0},
    },
)


TaskBasedStep = TaskBasedSettingInitStep
