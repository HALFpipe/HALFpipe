# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from copy import deepcopy
from itertools import chain, combinations
from typing import List, Optional

from ...model import InferredTypeContrastSchema, MissingFilterSchema, TContrastSchema
from ...utils.ops import ravel
from ..components import (
    MultiNumberInputView,
    MultipleChoiceInputView,
    MultiSingleChoiceInputView,
    SingleChoiceInputView,
    SpacerView,
    TextInputView,
    TextView,
)
from ..step import Step, YesNoStep
from ..utils import forbidden_chars
from .loop import AddAnotherModelStep
from .utils import format_column

next_step_type = AddAnotherModelStep


def apply_filters_to_variables(filters, variables):
    variables = deepcopy(variables)
    variablesdict = {v["name"]: v for v in variables}
    for filt in filters:
        if filt["type"] == "group":
            action = filt["action"]
            filterlevels = set(filt["levels"])
            if filt["variable"] in variablesdict:
                variable = variablesdict[filt["variable"]]
                varlevels = set(str(level) for level in variable["levels"])
                if action == "include":
                    varlevels &= filterlevels
                elif action == "exclude":
                    varlevels -= filterlevels
                variable["levels"] = [
                    level for level in variable["levels"] if level in varlevels
                ]  # maintain order
    variables = [
        variablesdict[variable["name"]]
        for variable in variables
        if variable["type"] != "categorical" or len(variable["levels"]) > 1
    ]
    return variables


class InteractionTermsStep(Step):
    def __init__(self, app, variables: List[str]):
        super(InteractionTermsStep, self).__init__(app)
        self.variables = variables

    def setup(self, _):
        self._append_view(
            TextView("Select which interaction terms to add to the model")
        )

        nvar = len(self.variables)

        terms = list(
            chain.from_iterable(
                combinations(self.variables, i) for i in range(2, nvar + 1)
            )
        )

        self.term_by_str = {" * ".join(termtpl): termtpl for termtpl in terms}

        self.options = list(self.term_by_str.keys())

        self.input_view = MultipleChoiceInputView(self.options, isVertical=True)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        return True

    def next(self, ctx):
        for var_str, is_checked in self.choice.items():
            if not is_checked:
                continue
            termtpl = list(self.term_by_str[var_str])

            contrast = InferredTypeContrastSchema().load(
                {"type": "infer", "variable": termtpl}
            )

            ctx.spec.models[-1].contrasts.append(contrast)

        return next_step_type(self.app)(ctx)


class InteractionVariablesStep(Step):
    def setup(self, ctx):
        self.choice: Optional[List[str]] = None

        self._append_view(
            TextView("Specify the variables for which to calculate interaction terms")
        )

        self.variables = ctx.database.metadata(
            ctx.spec.models[-1].spreadsheet, "variables"
        )
        self.variables = apply_filters_to_variables(
            ctx.spec.models[-1].filters, self.variables
        )
        contrastvariables = set(
            ravel(
                contrast["variable"]
                for contrast in ctx.spec.models[-1].contrasts
                if contrast.get("type") == "infer"
            )
        )  # names of all variables added to the model in the previous step
        self.variables = [
            variable
            for variable in self.variables
            if variable["name"] in contrastvariables
        ]

        assert len(self.variables) > 0, "No variables to calculate interaction terms"

        varnames = [variable["name"] for variable in self.variables]
        options = [format_column(varname) for varname in varnames]

        self.str_by_varname = dict(zip(varnames, options))

        self.input_view = MultipleChoiceInputView(options, isVertical=True)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        while True:
            checked = self.input_view()
            if checked is None:
                return False
            self.choice = [
                variable["name"]
                for variable in self.variables
                if checked[self.str_by_varname[variable["name"]]]
            ]
            if len(self.choice) > 1:
                break
        return True

    def next(self, ctx):
        if self.choice is None:
            self.choice = []
        return InteractionTermsStep(self.app, self.choice)(ctx)


class AddInteractionTerms(YesNoStep):
    header_str = "Specify interaction terms?"
    yes_step_type = InteractionVariablesStep
    no_step_type = next_step_type

    def _should_run(self, ctx):
        contrastvariables = set(
            ravel(
                contrast["variable"]
                for contrast in ctx.spec.models[-1].contrasts
                if contrast.get("type") == "infer"
            )
        )  # names of all variables added to the model in the previous step

        if len(contrastvariables) > 1:
            return True
        else:
            self.choice = "No"
            return False


class AddAnotherContrastStep(YesNoStep):
    header_str = "Add another contrast?"
    no_step_type = AddInteractionTerms


class ContrastValuesStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify contrast values"))

        (varname,) = ctx.spec.models[-1].contrasts[-1].get("variable")

        self.variables = ctx.database.metadata(
            ctx.spec.models[-1].spreadsheet, "variables"
        )
        self.variables = apply_filters_to_variables(
            ctx.spec.models[-1].filters, self.variables
        )

        variables_by_name = {variable["name"]: variable for variable in self.variables}

        variable = variables_by_name[varname]
        self.options = variable["levels"]

        self.input_view = MultiNumberInputView(self.options)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.valuedict = self.input_view()
        if self.valuedict is None:
            return False
        return True

    def next(self, ctx):
        ctx.spec.models[-1].contrasts[-1]["values"] = self.valuedict

        return AddAnotherContrastStep(self.app)(ctx)


class ContrastVariableStep(Step):
    def setup(self, ctx):
        self._append_view(
            TextView("Specify the categorical variable for this contrast")
        )

        self.variables = ctx.database.metadata(
            ctx.spec.models[-1].spreadsheet, "variables"
        )
        self.variables = apply_filters_to_variables(
            ctx.spec.models[-1].filters, self.variables
        )
        contrastvariables = set(
            ravel(
                contrast["variable"]
                for contrast in ctx.spec.models[-1].contrasts
                if contrast.get("type") == "infer"
            )
        )  # names of all variables added to the model in the previous step
        self.variables = [
            variable
            for variable in self.variables
            if variable["type"] == "categorical"
            and variable["name"] in contrastvariables
        ]

        varnames = [variable["name"] for variable in self.variables]
        options = [format_column(varname) for varname in varnames]

        self.varname_by_str = dict(zip(options, varnames))

        self.input_view = SingleChoiceInputView(options)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        return True

    def next(self, ctx):
        varname = self.varname_by_str[self.choice]
        ctx.spec.models[-1].contrasts[-1]["variable"] = [varname]

        return ContrastValuesStep(self.app)(ctx)


class ContrastNameStep(Step):
    def setup(self, ctx):
        if (
            not hasattr(ctx.spec.models[-1], "contrasts")
            or ctx.spec.models[-1].contrasts is None
        ):
            ctx.spec.models[-1].contrasts = []

        self.names = set(
            contrast["name"]
            for contrast in ctx.spec.models[-1].contrasts
            if "name" in contrast
        )

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
        self.value = None

    def run(self, _):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        assert self.result not in self.names, "Duplicate contrast name"

        contrast = TContrastSchema().load({"type": "t", "name": self.result})
        ctx.spec.models[-1].contrasts.append(contrast)

        return ContrastVariableStep(self.app)(ctx)


AddAnotherContrastStep.yes_step_type = ContrastNameStep


class HaveContrastsStep(YesNoStep):
    yes_step_type = ContrastNameStep
    no_step_type = AddInteractionTerms

    header_str = "Specify additional contrasts for categorical variables?"

    def _should_run(self, ctx):
        variables = ctx.database.metadata(ctx.spec.models[-1].spreadsheet, "variables")
        variables = apply_filters_to_variables(ctx.spec.models[-1].filters, variables)
        contrastvariables = set(
            ravel(
                contrast["variable"]
                for contrast in ctx.spec.models[-1].contrasts
                if contrast.get("type") == "infer"
            )
        )  # names of all variables added to the model in the previous step
        variables = [
            variable
            for variable in variables
            if variable["type"] == "categorical"
            and variable["name"] in contrastvariables
        ]
        if len(variables) == 0:
            self.choice = "No"
            return False
        return True

    def setup(self, ctx):
        instruction_str0 = (
            "Contrasts for the mean across all subjects, and for all variables "
        )
        self._append_view(TextView(instruction_str0))
        self._append_view(TextView("will be generated automatically"))
        self._append_view(SpacerView(1))

        super(HaveContrastsStep, self).setup(ctx)


class VariableMissingActionStep(Step):
    values = ["Listwise deletion", "Mean substitution"]

    def setup(self, ctx):
        self._append_view(TextView("Specify the action for missing values"))

        self.variables = ctx.database.metadata(
            ctx.spec.models[-1].spreadsheet, "variables"
        )
        self.variables = apply_filters_to_variables(
            ctx.spec.models[-1].filters, self.variables
        )
        self.variables = [
            variable for variable in self.variables if variable["type"] != "id"
        ]
        contrastvariables = set(
            ravel(
                contrast["variable"]
                for contrast in ctx.spec.models[-1].contrasts
                if contrast.get("type") == "infer"
            )
        )
        self.variables = [
            variable
            for variable in self.variables
            if variable["name"] in contrastvariables
        ]

        varnames = [variable["name"] for variable in self.variables]
        options = [format_column(varname) for varname in varnames]

        self.varname_by_str = dict(zip(options, varnames))

        self.input_view = MultiSingleChoiceInputView(options, self.values)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        return True

    def next(self, ctx):
        if self.choice is not None:
            for variable_str, value in self.choice.items():
                varname = self.varname_by_str[variable_str]

                if self.values.index(value) == 0:  # listwise deletion
                    # create filter
                    ctx.spec.models[-1].filters.append(
                        MissingFilterSchema().load(
                            {
                                "action": "exclude",
                                "type": "missing",
                                "variable": varname,
                            }
                        )
                    )

        return HaveContrastsStep(self.app)(ctx)


class VariableSelectStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify the variables to add to the model"))

        self.variables = ctx.database.metadata(
            ctx.spec.models[-1].spreadsheet, "variables"
        )
        self.variables = apply_filters_to_variables(
            ctx.spec.models[-1].filters, self.variables
        )
        self.variables = [
            variable for variable in self.variables if variable["type"] != "id"
        ]

        varnames = [variable["name"] for variable in self.variables]
        options = [format_column(varname) for varname in varnames]

        self.varname_by_str = dict(zip(options, varnames))

        self.input_view = MultipleChoiceInputView(options, checked=options)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.choice = self.input_view()
        if self.choice is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        if (
            not hasattr(ctx.spec.models[-1], "contrasts")
            or ctx.spec.models[-1].contrasts is None
        ):
            ctx.spec.models[-1].contrasts = []

        assert self.choice is not None
        checkedvarnames = set(
            self.varname_by_str[option]
            for option, checked in self.choice.items()
            if checked
        )

        for variable in self.variables:
            if variable["name"] in checkedvarnames:
                contrast = InferredTypeContrastSchema().load(
                    {"type": "infer", "variable": [variable["name"]]}
                )
                ctx.spec.models[-1].contrasts.append(contrast)

        return VariableMissingActionStep(self.app)(ctx)
