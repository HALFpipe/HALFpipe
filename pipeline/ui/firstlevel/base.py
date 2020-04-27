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
    SingleChoiceInputView,
)

from ...spec import Analysis, PreprocessedBoldTagsSchema, study_entities
from ..utils import (
    YesNoStep,
    BaseBOLDSelectStep,
    forbidden_chars,
)
from ..step import Step
from .task import TaskBasedStep
from .rest import (
    SeedBasedConnectivityStep,
    DualRegressionStep,
    AtlasBasedConnectivityStep,
    ReHoStep,
    FALFFStep,
)
from .loop import AddAnotherFirstLevelAnalysisStep

bold_tags_dict = {"datatype": "func", "suffix": "bold"}


def add_first_level_analysis_obj(ctx):
    analysis_tags_dict = {**bold_tags_dict, "space": "mni"}
    analysis_tags_obj = PreprocessedBoldTagsSchema().load(analysis_tags_dict)
    analysis_dict = {
        "level": "first",
        "tags": analysis_tags_obj,
    }
    analysis_obj = Analysis(**analysis_dict)
    ctx.add_analysis_obj(analysis_obj)


class BOLDSelectStep(BaseBOLDSelectStep):
    entities = study_entities

    def setup(self, ctx):
        self.is_first_run = True
        gen = ctx.database.get(**bold_tags_dict)
        assert gen is not None
        self.filepaths = list(gen)
        assert len(self.filepaths) > 0, "No BOLD images for analysis"
        db_entities, db_tags_set = ctx.database.get_multi_tagval_set(
            self.entities, filepaths=self.filepaths
        )
        dsp_entities = []
        self.tagval_by_str = []
        dsp_values = []
        for entity, tagvals in zip(db_entities, zip(*db_tags_set)):
            tagvals_set = set(tagvals)
            if len(tagvals_set) > 1:
                dsp_entities.append(entity)
                if len(tagvals_set) > 2:
                    filterval_by_value = [("Use all", None)]
                filterval_by_value += [
                    ("Use {}".format(self._format_tag(tagval)), tagval)
                    for tagval in tagvals_set
                ]
                self.tagval_by_str.append(dict(filterval_by_value))
                value_strs, _ = zip(*filterval_by_value)
                dsp_values.append(list(value_strs))
        self.entities = dsp_entities
        options = [self._tokenize_entity(entity) for entity in self.entities]
        self.should_run = True
        if len(options) == 0:
            self.should_run = False
            return
        self._append_view(TextView("Specify scans to use for this analysis"))
        self.input_view = MultiSingleChoiceInputView(options, dsp_values)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        if self.should_run:
            while True:
                tags_by_options = self.input_view()
                if tags_by_options is None:  # was cancelled
                    return False
                selectedtagdict = {
                    entity: self.tagval_by_str[i][tag_str]
                    for i, (entity, tag_str) in enumerate(
                        zip(self.entities, tags_by_options.values())
                    )
                    if self.tagval_by_str[i][tag_str] is not None
                }
                filepaths = ctx.database.get(**bold_tags_dict, **selectedtagdict)
                if filepaths is not None and len(filepaths) > 1:
                    break
            assert len(ctx.spec.analyses) > 0
            for i, (entity, tag_str) in enumerate(
                zip(self.entities, tags_by_options.values())
            ):
                tagval = self.tagval_by_str[i][tag_str]
                if tagval is not None:
                    setattr(ctx.spec.analyses[-1].tags, entity, tagval)
            return True
        return self.is_first_run

    def next(self, ctx):
        if self.should_run or self.is_first_run:
            self.is_first_run = False
            next_step_type = {
                "task_based": TaskBasedStep,
                "seed_based_connectivity": SeedBasedConnectivityStep,
                "dual_regression": DualRegressionStep,
                "atlas_based_connectivity": AtlasBasedConnectivityStep,
                "reho": ReHoStep,
                "falff": FALFFStep,
            }[ctx.spec.analyses[-1].type]
            return next_step_type(self.app)(ctx)
        return


class SubjectAnalysisNameStep(Step):
    nameSuggestionByAnalysisType = {
        "task_based": "taskBased",
        "seed_based_connectivity": "seedCorr",
        "dual_regression": "dualReg",
        "atlas_based_connectivity": "corrMatrix",
        "reho": "reHo",
        "falff": "fALFF",
    }

    def setup(self, ctx):
        self._append_view(TextView("Specify analysis name"))
        assert ctx.spec.analyses is not None and len(ctx.spec.analyses) > 0
        self.names = set(analysis.name for analysis in ctx.spec.analyses)
        baseSuggestion = self.nameSuggestionByAnalysisType[ctx.spec.analyses[-1].type]
        suggestion = baseSuggestion
        index = 1
        while suggestion in self.names:
            suggestion = f"{baseSuggestion}_{index}"
            index += 1
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
        return BOLDSelectStep(self.app)(ctx)


class FirstLevelAnalysisTypeStep(Step):
    is_vertical = True
    options = {
        "Task-based": "task_based",
        "Seed-based connectivity": "seed_based_connectivity",
        "Dual regression": "dual_regression",
        "Atlas-based connectivity matrix": "atlas_based_connectivity",
        "ReHo": "reho",
        "fALFF": "falff",
    }

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
        add_first_level_analysis_obj(ctx)
        if self.choice is None:
            return
        ctx.spec.analyses[-1].type = self.options[self.choice]
        return SubjectAnalysisNameStep(self.app)(ctx)


class HasFirstLevelAnalysisStep(YesNoStep):
    header_str = f"Specify subject-level analysis?"
    yes_step_type = FirstLevelAnalysisTypeStep
    no_step_type = None


AddAnotherFirstLevelAnalysisStep.yes_step_type = FirstLevelAnalysisTypeStep
