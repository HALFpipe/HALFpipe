# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import Optional

from calamities import (
    TextView,
    SpacerView,
    NumberInputView,
    MultiMultipleChoiceInputView,
)

from ..step import Step, YesNoStep, StepType
from ...model import (
    FilterSchema,
    GroupFilterSchema,
)

from .loop import AddAnotherModelStep
from .design import VariableSelectStep
from .utils import format_column


def get_cutoff_filter_steps(cutoff_filter_next_step_type):
    class BaseCutoffFilterStep(Step):
        number_input_args = dict()

        header_str: Optional[str] = None
        filter_field: Optional[str] = None

        next_step_type: Optional[StepType] = None

        def setup(self, ctx):
            self._append_view(TextView(self.header_str))

            self.input_view = NumberInputView(**self.number_input_args)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

        def run(self, ctx):
            self.cutoff = self.input_view()
            if self.cutoff is None:  # was cancelled
                return False
            return True

        def next(self, ctx):
            if not hasattr(ctx.spec.models[-1], "filters") or ctx.spec.models[-1].filters is None:
                ctx.spec.models[-1].filters = []

            filter_obj = FilterSchema().load(
                {
                    "type": "cutoff",
                    "field": self.filter_field,
                    "action": "exclude",
                    "cutoff": self.cutoff,
                }
            )
            ctx.spec.models[-1].filters.append(filter_obj)

            return self.next_step_type(self.app)(ctx)

    class FdPercFilterStep(BaseCutoffFilterStep):
        filter_field = "fd_perc"
        number_input_args = {"number": 0.1, "min": 0, "max": 1}
        next_step_type = cutoff_filter_next_step_type

        def setup(self, ctx):
            fd_thres = ctx.spec.global_settings.get("fd_thres")
            self.header_str = "Specify the maximum allowed proportion of frames " + \
                f"above the framewise displacement threshold of {fd_thres:.1f} mm"
            super(FdPercFilterStep, self).setup(ctx)

    class FdMeanFilterStep(BaseCutoffFilterStep):
        header_str = "Specify the maximum allowed mean framewise displacement in mm"
        filter_field = "fd_mean"
        number_input_args = {"number": 0.5, "min": 0}
        next_step_type = FdPercFilterStep

    class MotionFilterStep(YesNoStep):
        header_str = "Exclude subjects based on movement?"
        yes_step_type = FdMeanFilterStep
        no_step_type = cutoff_filter_next_step_type

    return MotionFilterStep


MEModelMotionFilterStep = get_cutoff_filter_steps(AddAnotherModelStep)
LMEModelMotionFilterStep = get_cutoff_filter_steps(VariableSelectStep)


class SubjectGroupFilterStep(Step):
    def setup(self, ctx):
        self.is_first_run = True
        self.should_run = False

        self.variables = ctx.database.metadata(ctx.spec.models[-1].spreadsheet, "variables")
        self.variables = [
            variable.copy()
            for variable in self.variables
            if variable["type"] == "categorical"
        ]

        if len(self.variables) > 0:
            self.should_run = True

            self._append_view(TextView("Specify the subjects to use"))
            self._append_view(SpacerView(1))

            instruction_str0 = (
                "Select the subjects to include in this analysis by their categorical variables"
            )
            self._append_view(TextView(instruction_str0))
            instruction_str1 = (
                "For multiple categorical variables, the intersection of the groups will be used"
            )
            self._append_view(TextView(instruction_str1))

            options = [format_column(variable["name"]) for variable in self.variables]
            values = [[*variable["levels"]] for variable in self.variables]  # make copy

            self.input_view = MultiMultipleChoiceInputView(options, values, checked=values)

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if not self.should_run:
            return self.is_first_run
        else:
            while True:
                self.choice = self.input_view()
                if self.choice is None:
                    return False
                is_valid = True
                for checked in self.choice:
                    if not any(checked.values()):
                        is_valid = False
                if is_valid:
                    return True

    def next(self, ctx):
        if not hasattr(ctx.spec.models[-1], "filters") or ctx.spec.models[-1].filters is None:
            ctx.spec.models[-1].filters = []

        for variable, checked in zip(self.variables, self.choice):
            if not all(checked.values()):
                levels = [str(k) for k, is_selected in checked.items() if is_selected]
                ctx.spec.models[-1].filters.append(
                    GroupFilterSchema().load(
                        {
                            "action": "include",
                            "type": "group",
                            "variable": variable["name"],
                            "levels": levels,
                        }
                    )
                )

        if self.should_run or self.is_first_run:
            self.is_first_run = False
            return LMEModelMotionFilterStep(self.app)(ctx)
