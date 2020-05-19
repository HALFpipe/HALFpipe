# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""


from calamities import (
    TextView,
    SpacerView,
    MultiSingleChoiceInputView,
    TextInputView,
    MultipleChoiceInputView,
    NumberInputView,
    FileInputView,
    TextElement,
    SingleChoiceInputView,
    MultiMultipleChoiceInputView,
    MultiNumberInputView,
)

import logging
import inflect
from inflection import camelize
from copy import deepcopy
from itertools import combinations, chain

from .utils import YesNoStep, make_name_suggestion, forbidden_chars
from .step import Step
from ..spec import (
    Analysis,
    FilterSchema,
    BoldTagsSchema,
    FixedEffectsHigherLevelAnalysisSchema,
    Variable,
    GroupFilterSchema,
    Contrast,
)
from ..database import bold_entities
from ..io import load_spreadsheet

p = inflect.engine()


def add_group_level_analysis_obj(ctx):
    analysis_dict = {"level": "higher", "across": "subject"}
    analysis_obj = Analysis(**analysis_dict)
    ctx.add_analysis_obj(analysis_obj)


def _format_column(colname):
    return f'"{colname}"'


class AddAnotherGroupLevelAnalysisStep(YesNoStep):
    header_str = "Add another group-level analysis?"
    yes_step_type = None  # add later, because not yet defined
    no_step_type = None


class InteractionTermsStep(Step):
    def __init__(self, app, variables):
        super(InteractionTermsStep, self).__init__(app)
        self.variables = variables

    def setup(self, ctx):
        self._append_view(TextView("Select which interaction terms to add to the model"))
        nvar = len(self.variables)
        terms = list(
            chain.from_iterable(combinations(self.variables, i) for i in range(2, nvar + 1))
        )
        self.term_by_str = {" * ".join(termtpl): termtpl for termtpl in terms}
        self.options = list(self.term_by_str.keys())
        self.input_view = MultipleChoiceInputView(self.options, isVertical=True)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        checked = self.input_view()
        if checked is None:
            return False
        for var_str, is_checked in checked.items():
            if is_checked:
                termtpl = list(self.term_by_str[var_str])
                ctx.spec.analyses[-1].contrasts.append(Contrast(variable=termtpl, type="infer"))
        return True

    def next(self, ctx):
        return AddAnotherGroupLevelAnalysisStep(self.app)(ctx)


class InteractionVariablesStep(Step):
    def setup(self, ctx):
        self._append_view(
            TextView("Specify the variables for which to calculate interaction terms")
        )
        assert (
            len(ctx.spec.analyses[-1].variables) > 0
        ), "No variables to calculate interaction terms"
        self.varname_by_str = {
            _format_column(variable.name): variable.name
            for variable in ctx.spec.analyses[-1].variables
            if variable.type != "id"
        }
        self.options = list(self.varname_by_str.keys())
        self.input_view = MultipleChoiceInputView(self.options, isVertical=True)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            checked = self.input_view()
            if checked is None:
                return False
            self.variables = [
                self.varname_by_str[var_str]
                for var_str, is_checked in checked.items()
                if is_checked
            ]
            if len(self.variables) > 1:
                break
        return True

    def next(self, ctx):
        return InteractionTermsStep(self.app, self.variables)(ctx)


class AddInteractionTerms(YesNoStep):
    header_str = "Specify interaction terms?"
    yes_step_type = InteractionVariablesStep
    no_step_type = AddAnotherGroupLevelAnalysisStep


class AddAnotherContrastStep(YesNoStep):
    header_str = "Add another contrast?"
    yes_step_type = None  # add later, because not yet defined
    no_step_type = AddInteractionTerms


class ContrastValuesStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify contrast values"))
        varnames = ctx.spec.analyses[-1].contrasts[-1].variable
        if len(varnames) == 1:
            varname = varnames[0]
            for variable in ctx.spec.analyses[-1].variables:
                if variable.name == varname:
                    break
            self.options = variable.levels
        else:
            raise NotImplementedError
        self.input_view = MultiNumberInputView(self.options)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        valuedict = self.input_view()
        if valuedict is None:
            return False
        ctx.spec.analyses[-1].contrasts[-1].values = valuedict
        return True

    def next(self, ctx):
        return AddAnotherContrastStep(self.app)(ctx)


class ContrastVariableStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify the categorical variable for this contrast"))
        self.varname_by_str = {
            _format_column(variable.name): variable.name
            for variable in ctx.spec.analyses[-1].variables
            if variable.type == "categorical"
        }
        self.options = list(self.varname_by_str.keys())
        self.input_view = SingleChoiceInputView(self.options)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        var_str = self.input_view()
        if var_str is None:
            return False
        varname = self.varname_by_str[var_str]
        ctx.spec.analyses[-1].contrasts[-1].variable = [varname]
        return True

    def next(self, ctx):
        return ContrastValuesStep(self.app)(ctx)


class ContrastNameStep(Step):
    def setup(self, ctx):
        if ctx.spec.analyses[-1].contrasts is None:
            index = 1
        else:
            index = min(1, len(ctx.spec.analyses[-1].contrasts))
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
                if ctx.spec.analyses[-1].contrasts is None:
                    ctx.spec.analyses[-1].contrasts = []
                for contrast in ctx.spec.analyses[-1].contrasts:
                    if contrast.name == value:
                        continue
                ctx.spec.analyses[-1].contrasts.append(Contrast(name=value, type="t"))
                break
        return True

    def next(self, ctx):
        return ContrastVariableStep(self.app)(ctx)


AddAnotherContrastStep.yes_step_type = ContrastNameStep


class HaveContrastsStep(YesNoStep):
    yes_step_type = ContrastNameStep
    no_step_type = AddInteractionTerms

    def setup(self, ctx):
        self._append_view(
            TextView(
                "Contrasts for the mean across all subjects, and for all variables "
                "will be generated automatically"
            )
        )
        self._append_view(SpacerView(1))
        # generate contrasts automatically
        if ctx.spec.analyses[-1].contrasts is None:
            ctx.spec.analyses[-1].contrasts = []
        for variable in ctx.spec.analyses[-1].variables:
            if variable.type != "id":
                ctx.spec.analyses[-1].contrasts.append(
                    Contrast(variable=[variable.name], type="infer")
                )
        self._append_view(TextView("Specify additional contrasts for categorical variables?"))
        super(HaveContrastsStep, self).setup(ctx)


class VariableSelectStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify the variables to add to the model"))
        self.variables = [
            variable for variable in ctx.spec.analyses[-1].variables if variable.type != "id"
        ]
        self.varname_by_str = {
            _format_column(variable.name): variable.name for variable in self.variables
        }
        options = list(self.varname_by_str.keys())
        self.input_view = MultipleChoiceInputView(options, checked=options)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        filterdict = self.input_view()
        if filterdict is None:  # was cancelled
            return False
        checkedvarnames = set(
            self.varname_by_str[varname] for varname, checked in filterdict.items() if checked
        )
        ctx.spec.analyses[-1].variables = [
            variable
            for variable in ctx.spec.analyses[-1].variables
            if variable.type == "id" or variable.name in checkedvarnames
        ]
        return True

    def next(self, ctx):
        return HaveContrastsStep(self.app)(ctx)


class BaseCutoffFilterStep(Step):
    def setup(self, ctx):
        self._append_view(TextView(self.header_str))
        self.input_view = NumberInputView(**self.kwargs)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        cutoff = self.input_view()
        if cutoff is None:  # was cancelled
            return False
        if ctx.spec.analyses[-1].filter is None:
            ctx.spec.analyses[-1].filter = []
        filter_obj = FilterSchema().load({"type": self.filter_type, "cutoff": cutoff})
        ctx.spec.analyses[-1].filter.append(filter_obj)
        return True


class FdGt0_5FilterStep(BaseCutoffFilterStep):
    header_str = (
        "Specify the maximum allowed proportion of frames with (FramewiseDisplacement > 0.5)"
    )
    filter_type = "fd_gt_0_5"
    kwargs = {"number": 0.1, "min": 0, "max": 1}
    next_step_type = VariableSelectStep

    def next(self, ctx):
        return self.next_step_type(self.app)(ctx)


class InterceptOnlyFdGt0_5FilterStep(FdGt0_5FilterStep):
    next_step_type = AddAnotherGroupLevelAnalysisStep


class MeanFdFilterStep(BaseCutoffFilterStep):
    header_str = "Specify the maximum allowed mean(FramewiseDisplacement)"
    filter_type = "mean_fd"
    kwargs = {"number": 0.5, "min": 0}
    next_step_type = FdGt0_5FilterStep

    def next(self, ctx):
        return self.next_step_type(self.app)(ctx)


class InterceptOnlyMeanFdFilterStep(MeanFdFilterStep):
    next_step_type = InterceptOnlyFdGt0_5FilterStep


class GroupLevelAnalysisMotionFilterStep(YesNoStep):
    header_str = "Exclude subjects based on movement?"
    yes_step_type = MeanFdFilterStep
    no_step_type = VariableSelectStep


class InterceptOnlyGroupLevelAnalysisMotionFilterStep(GroupLevelAnalysisMotionFilterStep):
    yes_step_type = InterceptOnlyMeanFdFilterStep
    no_step_type = AddAnotherGroupLevelAnalysisStep


class SubjectGroupFilterStep(Step):
    def setup(self, ctx):
        self.is_first_run = True
        self.is_missing = False
        self.variables = [
            variable
            for variable in ctx.spec.analyses[-1].variables
            if variable.type == "categorical"
        ]
        if len(self.variables) > 0:
            self.is_missing = True
            self._append_view(TextView("Specify the subjects to use"))
            self._append_view(SpacerView(1))
            self._append_view(
                TextView(
                    "Select the subjects to include in this analysis by their categorical variables"
                )
            )
            self._append_view(
                TextView(
                    "If you specify selections across different categorical variables, "
                    "the intersection of the groups will be used"
                )
            )
            options = [_format_column(variable.name) for variable in self.variables]
            values = [variable.levels for variable in self.variables]
            self.input_view = MultiMultipleChoiceInputView(options, values, checked=values)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if not self.is_missing:
            return True
        if ctx.spec.analyses[-1].filter is None:
            ctx.spec.analyses[-1].filter = []
        while True:
            filterdictlist = self.input_view()
            if filterdictlist is None:  # was cancelled
                return False
            is_valid = True
            for checked in filterdictlist:
                if not any(checked.values()):
                    is_valid = False
                    break
            if is_valid:
                for variable, checked in zip(self.variables, filterdictlist):
                    if not all(checked.values()):
                        levels = [k for k, is_selected in checked.items() if is_selected]
                        ctx.spec.analyses[-1].filter.append(
                            GroupFilterSchema().load(
                                {
                                    "action": "include",
                                    "type": "group",
                                    "variable": variable.name,
                                    "levels": levels,
                                }
                            )
                        )
                break
        return True

    def next(self, ctx):
        if self.is_missing or self.is_first_run:
            self.is_first_run = False
            return GroupLevelAnalysisMotionFilterStep(self.app)(ctx)
        else:
            return


class SpreadsheetColumnTypeStep(Step):
    def __init__(self, app, df):
        super(SpreadsheetColumnTypeStep, self).__init__(app)
        self.df = df

    def setup(self, ctx):
        self.is_first_run = True
        self.is_missing = True
        already_used = set(variable.name for variable in ctx.spec.analyses[-1].variables)
        if all(column in already_used for column in self.df):
            self.is_missing = False
        if self.is_missing:
            self._append_view(TextView("Specify the column data types"))
            if ctx.spec.analyses[-1].variables is None:
                ctx.spec.analyses[-1].variables = []
            self.varname_by_str = {
                _format_column(column): column for column in self.df if column not in already_used
            }
            options = list(self.varname_by_str.keys())
            values = ["Continuous", "Categorical"]
            self.input_view = MultiSingleChoiceInputView(options, values)
            self.input_view.selectedIndices = [
                1 if self.df[column].dtype == object else 0
                for column in self.varname_by_str.values()
            ]
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if self.is_missing:
            valuedict = self.input_view()
            if valuedict is None:  # was cancelled
                return False
            for variable_str, value in valuedict.items():
                varname = self.varname_by_str[variable_str]
                vartype = value.lower()
                varobj = Variable(name=varname, type=vartype)
                if vartype == "categorical":
                    varobj.levels = self.df[varname].astype(str).unique().tolist()
                ctx.spec.analyses[-1].variables.append(varobj)
        return True

    def next(self, ctx):
        if self.is_missing or self.is_first_run:
            self.is_first_run = False
            return SubjectGroupFilterStep(self.app)(ctx)
        else:
            return


class SpreadsheetIdColumnStep(Step):
    def __init__(self, app, df):
        super(SpreadsheetIdColumnStep, self).__init__(app)
        self.df = df

    def setup(self, ctx):
        self.is_first_run = True
        self.is_missing = True
        if any(variable.type == "id" for variable in ctx.spec.analyses[-1].variables):
            self.is_missing = False
        if self.is_missing:
            self._append_view(TextView("Specify the column containing subject names"))
            if ctx.spec.analyses[-1].variables is None:
                ctx.spec.analyses[-1].variables = []
            already_used = set(variable.name for variable in ctx.spec.analyses[-1].variables)
            self.varname_by_str = {
                _format_column(column): column for column in self.df if column not in already_used
            }
            options = list(self.varname_by_str.keys())
            self.input_view = SingleChoiceInputView(options, isVertical=True)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if self.is_missing:
            option_str = self.input_view()
            if option_str is None:  # was cancelled
                return False
            varname = self.varname_by_str[option_str]
            ctx.spec.analyses[-1].variables.append(Variable(name=varname, type="id"))
        return True

    def next(self, ctx):
        if self.is_missing or self.is_first_run:
            self.is_first_run = False
            return SpreadsheetColumnTypeStep(self.app, self.df)(ctx)
        else:
            return


class SpreadsheetStep(Step):
    def _messagefun(self):
        return self.message

    def setup(self, ctx):
        self._append_view(TextView("Specify the covariates/group data spreadsheet file"))
        self.message = None
        self.input_view = FileInputView(base_path=ctx.spreadsheet_file, messagefun=self._messagefun)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            filepath = self.input_view()
            if filepath is None:  # was cancelled
                return False
            try:
                self.df = load_spreadsheet(filepath)
                for analysis_obj in ctx.spec.analyses:
                    if (
                        analysis_obj.level == "higher"
                        and analysis_obj.type == "glm"
                        and analysis_obj.spreadsheet == filepath
                    ):
                        ctx.spec.analyses[-1].variables = deepcopy(analysis_obj.variables)
                        break
                if ctx.spec.analyses[-1].variables is None:
                    ctx.spec.analyses[-1].variables = []
                ctx.spec.analyses[-1].spreadsheet = filepath
                break
            except Exception as e:
                logging.getLogger("pipeline.ui").exception("Exception: %s", e)
                error_color = self.app.layout.color.red
                self.message = TextElement(str(e), color=error_color)
        return True

    def next(self, ctx):
        return SpreadsheetIdColumnStep(self.app, self.df)(ctx)


class GroupLevelAnalysisAggregateStep(Step):
    aggregate_order = ["direction", "run", "session"]

    def _resolve_tags(self, ctx):
        analysis_obj = ctx.spec.analyses[-1]
        input = set(analysis_obj.input)
        assert input is not None and len(input) > 0

        firstlevel_analysis_objs = []
        for obj in ctx.spec.analyses:
            if obj.name in input:
                if obj.level == "first":
                    firstlevel_analysis_objs.append(obj)

        entities_by_analysis = {
            analysis_obj.name: set() for analysis_obj in firstlevel_analysis_objs
        }
        for analysis_obj in firstlevel_analysis_objs:
            tagdict = BoldTagsSchema().dump(analysis_obj.tags)
            tagdict = {
                k: v
                for k, v in tagdict.items()
                if k in self.aggregate_order or k in {"datatype", "suffix", "extension"}
            }
            filepaths = ctx.database.get(**tagdict)
            for entity in bold_entities:
                tagvalset = ctx.database.get_tagval_set(entity, filepaths=filepaths)
                if tagvalset is not None and len(tagvalset) > 1:
                    entities_by_analysis[analysis_obj.name].add(entity)
        return entities_by_analysis

    def _get_fixed_effects_aggregate(self, ctx, name, across):
        for i, analysis_obj in enumerate(ctx.spec.analyses):
            if (
                analysis_obj.level == "higher"
                and analysis_obj.type == "fixed_effects"
                and name in analysis_obj.input
                and len(analysis_obj.input) == 1
                and across == analysis_obj.across
                and analysis_obj.filter is None
            ):
                return analysis_obj.name
        # need to create
        acrossstr = camelize(p.plural(across))
        basename = f"Aggregate_{name}_Across_{acrossstr}"
        aggregatename = basename
        analysis_names = set(analysis_obj.name for analysis_obj in ctx.spec.analyses)
        i = 0
        while aggregatename in analysis_names:  # assure unique name
            aggregatename = f"{basename}{i}"
            i += 1
        analysis_obj = FixedEffectsHigherLevelAnalysisSchema().load(
            {
                "level": "higher",
                "type": "fixed_effects",
                "name": aggregatename,
                "input": [name],
                "across": across,
            }
        )
        ctx.spec.analyses.insert(-1, analysis_obj)
        return analysis_obj.name

    def setup(self, ctx):
        self.is_first_run = True
        self.entities_by_analysis = self._resolve_tags(ctx)
        entitiesset = set.union(*[set(entities) for entities in self.entities_by_analysis.values()])
        entitiesset &= set(self.aggregate_order)
        across = ctx.spec.analyses[-1].across
        if across in entitiesset:
            entitiesset.remove(across)
        self.entities = list(entitiesset)
        self.options = [
            p.inflect(f"Aggregate across plural('{entity}')") for entity in self.entities
        ]
        self.optionstr_by_entity = {k: v for k, v in zip(self.entities, self.options)}
        if len(self.options) > 0:
            self._append_view(TextView("Aggregate scan-level statistics before analysis?"))
            self.input_view = MultipleChoiceInputView(self.options, checked=self.options)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if len(self.options) > 0:
            res = self.input_view()
            if res is None:  # was cancelled
                return False
            ordered_entities_to_aggregate = [
                entity
                for entity in self.aggregate_order
                if entity in self.optionstr_by_entity
                and self.optionstr_by_entity[entity] in res
                and res[self.optionstr_by_entity[entity]]
            ]
            analysis_obj = ctx.spec.analyses[-1]
            while len(ordered_entities_to_aggregate) > 0:
                across = ordered_entities_to_aggregate.pop(0)
                new_entities_by_analysis = {}
                for analysis_name, entities in self.entities_by_analysis.items():
                    if across in entities:
                        new_analysis_name = self._get_fixed_effects_aggregate(
                            ctx, analysis_name, across
                        )
                        entities.remove(across)
                        new_entities_by_analysis[new_analysis_name] = entities
                    else:
                        new_entities_by_analysis[analysis_name] = entities
                self.entities_by_analysis = new_entities_by_analysis
            analysis_obj.input = list(self.entities_by_analysis.keys())
        return True

    def next(self, ctx):
        if len(self.options) > 0 or self.is_first_run:
            self.is_first_run = False
            next_step_type = {
                "intercept_only": InterceptOnlyGroupLevelAnalysisMotionFilterStep,
                "glm": SpreadsheetStep,
            }[ctx.spec.analyses[-1].type]
            return next_step_type(self.app)(ctx)
        else:
            return


class GroupLevelAnalysisInputStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Select subject-level analyses to include in this analysis"))
        assert ctx.spec.analyses is not None
        namesset = set()
        for analysis in ctx.spec.analyses:
            assert analysis.level is not None
            if analysis.level == "first":
                namesset.add(analysis.name)
        names = list(namesset)
        self.input_view = MultipleChoiceInputView(names, checked=names)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        if ctx.spec.analyses[-1].input is None:
            ctx.spec.analyses[-1].input = []
        while not len(ctx.spec.analyses[-1].input) > 0:
            inputdict = self.input_view()
            if inputdict is None:  # was cancelled
                return False
            for name, is_selected in inputdict.items():
                if is_selected:
                    ctx.spec.analyses[-1].input.append(name)
        return True

    def next(self, ctx):
        return GroupLevelAnalysisAggregateStep(self.app)(ctx)


class GroupLevelAnalysisNameStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify analysis name"))
        assert ctx.spec.analyses is not None
        self.names = set(analysis.name for analysis in ctx.spec.analyses)
        index = 0
        for analysis in ctx.spec.analyses:
            assert analysis.level is not None
            if analysis.level == "higher" and analysis.across == "subject":
                index += 1
        suggestion = make_name_suggestion("group", "analysis", index=index)
        self.input_view = TextInputView(text=suggestion)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            self._name = self.input_view()
            if self._name is None:  # was cancelled
                return False
            if forbidden_chars.search(self._name) is None and self._name not in self.names:
                return True
            else:
                pass  # TODO add messagefun

    def next(self, ctx):
        assert self._name not in self.names, "Duplicate analysis name"
        ctx.spec.analyses[-1].name = self._name
        return GroupLevelAnalysisInputStep(self.app)(ctx)


class GroupLevelAnalysisTypeStep(Step):
    is_vertical = True
    options = {"Intercept-only": "intercept_only", "GLM": "glm"}

    def setup(self, ctx):
        self._append_view(TextView("Specify the analysis type"))
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
        add_group_level_analysis_obj(ctx)
        if self.choice is None:
            return
        ctx.spec.analyses[-1].type = self.options[self.choice]
        return GroupLevelAnalysisNameStep(self.app)(ctx)


class HasGroupLevelAnalysisStep(YesNoStep):
    header_str = "Specify group-level analysis?"
    yes_step_type = GroupLevelAnalysisTypeStep
    no_step_type = None


AddAnotherGroupLevelAnalysisStep.yes_step_type = GroupLevelAnalysisTypeStep

GroupLevelAnalysisStep = HasGroupLevelAnalysisStep
