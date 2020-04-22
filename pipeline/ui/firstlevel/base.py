# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from calamities import TextView, SpacerView, MultiSingleChoiceInputView, TextInputView


from ...spec import Analysis, PreprocessedBoldTagsSchema, study_entities
from ..utils import (
    YesNoStep,
    BranchStep,
    BaseBOLDSelectStep,
    make_name_suggestion,
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


class FirstLevelAnalysisTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the analysis type"
    options = {
        "Task-based": TaskBasedStep,
        "Seed-based connectivity": SeedBasedConnectivityStep,
        "Dual regression": DualRegressionStep,
        "Atlas-based connectivity matrix": AtlasBasedConnectivityStep,
        "ReHo": ReHoStep,
        "fALFF": FALFFStep,
    }

    def next(self, ctx):
        ctx.spec.analyses[-1].type = {
            "Task-based": "task_based",
            "Seed-based connectivity": "seed_based_connectivity",
            "Dual regression": "dual_regression",
            "Atlas-based connectivity matrix": "atlas_based_connectivity",
            "ReHo": "reho",
            "fALFF": "falff",
        }[self.choice]
        return super(FirstLevelAnalysisTypeStep, self).next(ctx)


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
            return FirstLevelAnalysisTypeStep(self.app)(ctx)
        return


class SubjectAnalysisNameStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify analysis name"))
        index = 1
        if ctx.spec.analyses is not None:
            index = len(ctx.spec.analyses) + 1
        suggestion = make_name_suggestion("analysis", index=index)
        self.input_view = TextInputView(text=suggestion)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            name = self.input_view()
            if name is None:  # was cancelled
                return False
            if forbidden_chars.search(name) is None:
                analysis_tags_dict = {**bold_tags_dict, "space": "mni"}
                analysis_tags_obj = PreprocessedBoldTagsSchema().load(analysis_tags_dict)
                analysis_dict = {
                    "name": name,
                    "level": "first",
                    "tags": analysis_tags_obj,
                }
                analysis_obj = Analysis(**analysis_dict)
                ctx.add_analysis_obj(analysis_obj)
                break
            else:
                pass  # TODO add messagefun
        return True

    def next(self, ctx):
        return BOLDSelectStep(self.app)(ctx)


class HasFirstLevelAnalysisStep(YesNoStep):
    header_str = f"Specify subject-level analysis?"
    yes_step_type = SubjectAnalysisNameStep
    no_step_type = None


AddAnotherFirstLevelAnalysisStep.yes_step_type = SubjectAnalysisNameStep
