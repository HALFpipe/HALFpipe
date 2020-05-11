# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import (
    TextView,
    SpacerView,
    MultiSingleChoiceInputView,
    MultiNumberInputView,
)


import numpy as np

from .pattern import FilePatternStep, FilePatternSummaryStep
from ..spec import (
    PEPOLARTagsSchema,
    PhaseDifferenceTagsSchema,
    Phase1TagsSchema,
    Phase2TagsSchema,
    Magnitude1TagsSchema,
    Magnitude2TagsSchema,
    FieldMapTagsSchema,
    PhaseEncodingDirection,
    bold_entities,
)
from .firstlevel import FirstLevelAnalysisStep

from .utils import (
    BranchStep,
    YesNoStep,
    NumericMetadataStep,
    BaseBOLDSelectStep,
)


class FmapSummaryStep(FilePatternSummaryStep):
    filetype_str = "field-map"
    tags_dict = {"datatype": "fmap"}
    allowed_entities = bold_entities
    next_step_type = FirstLevelAnalysisStep


class BaseBOLDMissingMetadataStep(BaseBOLDSelectStep):
    tags_dict = {"datatype": "func", "suffix": "bold"}
    entities = ["session", "run", "task"]

    def __init__(self, app, show_header=True):
        super(BaseBOLDMissingMetadataStep, self).__init__(app)
        self.show_header = show_header

    def _setup_header(self):
        if self.show_header:
            self._append_view(TextView("Specify missing metadata for BOLD images"))
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if self.has_missing:
            res_by_str = self.input_view()
            if res_by_str is None:  # was cancelled
                return False
            for k, res in res_by_str.items():
                tags = self.tags_by_str[k]
                filterdict = {k: v for k, v in zip(self.entities, tags)}
                filepaths = ctx.database.filter(self.filepaths_with_missing_metadata, **filterdict)
                fileobj_set = set(ctx.database.get_fileobj(filepath) for filepath in filepaths)
                for fileobj in fileobj_set:
                    self._set_value(fileobj, res)
        return True


class BoldDirectionStep(BaseBOLDMissingMetadataStep):
    values = [
        "Anterior to posterior",
        "Posterior to anterior",
        "Left to right",
        "Right to left",
        "Inferior to superior",
        "Superior to inferior",
    ]

    def setup(self, ctx):
        filepaths = ctx.database.get(**self.tags_dict)
        filepaths_without_pedir = [
            filepath
            for filepath in filepaths
            if ctx.database.get_tags(filepath).phase_encoding_direction is None
        ]
        self.filepaths_with_missing_metadata = filepaths_without_pedir
        self.has_missing = False
        if len(filepaths_without_pedir) > 0:
            self.has_missing = True
            self._setup_header()
            self._append_view(TextView("Specify phase encoding direction"))
            options = self._setup_options(ctx, filepaths_without_pedir)
            self.input_view = MultiSingleChoiceInputView(options, self.values)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def _set_value(self, fileobj, res):
        pedir_obj = PhaseEncodingDirection[res]
        assert (
            fileobj.tags.phase_encoding_direction is None
            or fileobj.tags.phase_encoding_direction == pedir_obj.value
        ), "Inconsistent phase encoding directions"
        fileobj.tags.phase_encoding_direction = pedir_obj.value

    def next(self, ctx):
        return FirstLevelAnalysisStep(self.app)(ctx)


class BoldEffectiveEchoSpacingStep(BaseBOLDMissingMetadataStep):
    def setup(self, ctx):
        filepaths = ctx.database.get(**self.tags_dict)
        filepaths_without_ees = [
            filepath
            for filepath in filepaths
            if ctx.database.get_tags(filepath).effective_echo_spacing is None
        ]
        self.filepaths_with_missing_metadata = filepaths_without_ees
        self.has_missing = False
        if len(filepaths_without_ees) > 0:
            self.has_missing = True
            self._setup_header()
            self._append_view(TextView("Specify effective_echo_spacing"))
            options = self._setup_options(ctx, filepaths_without_ees)
            self.input_view = MultiNumberInputView(options, min=0)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def _set_value(self, fileobj, res):
        ees = float(res)
        assert fileobj.tags.effective_echo_spacing is None or np.isclose(
            fileobj.tags.effective_echo_spacing, ees
        ), "Inconsistent effective echo spacing"
        fileobj.tags.effective_echo_spacing = ees

    def next(self, ctx):
        return BoldDirectionStep(self.app, show_header=False)(ctx)


class FieldMapStep(FilePatternStep):
    filetype_str = "field-map image"
    tags_dict = {"datatype": "fmap", "suffix": "fieldmap"}
    allowed_entities = ["subject", "session", "run", "task"]
    ask_if_missing_entities = []
    required_in_pattern_entities = ["subject"]
    next_step_type = BoldEffectiveEchoSpacingStep
    tags_schema = FieldMapTagsSchema()


class PhaseDifferenceEchoTimeStep(NumericMetadataStep):
    header_str = "Specify the echo time difference in seconds"
    min = 0
    entity = "echo_time_difference"
    next_step_type = BoldEffectiveEchoSpacingStep


class PhaseDifferenceStep(FilePatternStep):
    filetype_str = "phase difference image"
    tags_dict = {"datatype": "fmap", "suffix": "phase1"}
    allowed_entities = ["subject", "session", "run", "task"]
    ask_if_missing_entities = []
    required_in_pattern_entities = ["subject"]
    next_step_type = PhaseDifferenceEchoTimeStep
    tags_schema = PhaseDifferenceTagsSchema()


class Phase2EchoTimeStep(NumericMetadataStep):
    header_str = "Specify the echo time in seconds"
    min = 0
    entity = "echo_time"
    next_step_type = BoldEffectiveEchoSpacingStep


class Phase2Step(FilePatternStep):
    filetype_str = "second set of phase image"
    tags_dict = {"datatype": "fmap", "suffix": "phase2"}
    allowed_entities = ["subject", "session", "run", "task"]
    ask_if_missing_entities = []
    required_in_pattern_entities = ["subject"]
    next_step_type = Phase2EchoTimeStep
    tags_schema = Phase2TagsSchema()


class Phase1EchoTimeStep(Phase2EchoTimeStep):
    next_step_type = Phase2Step


class Phase1Step(FilePatternStep):
    filetype_str = "first set of phase image"
    tags_dict = {"datatype": "fmap", "suffix": "phase1"}
    allowed_entities = ["subject", "session", "run", "task"]
    ask_if_missing_entities = []
    required_in_pattern_entities = ["subject"]
    next_step_type = Phase1EchoTimeStep
    tags_schema = Phase1TagsSchema()


class PhaseTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the type of the phase images"
    options = {
        "One phase difference image": PhaseDifferenceStep,
        "Two phase images": Phase1Step,
    }


class PhaseDifferenceMagnitude2Step(FilePatternStep):
    filetype_str = "second set of magnitude image"
    tags_dict = {"datatype": "fmap", "suffix": "magnitude2"}
    allowed_entities = ["subject", "session", "run", "task"]
    ask_if_missing_entities = []
    required_in_pattern_entities = ["subject"]
    next_step_type = PhaseTypeStep
    tags_schema = Magnitude2TagsSchema()


class PhaseDifferenceOnlyMagnitude1Step(PhaseDifferenceMagnitude2Step):
    filetype_str = "magnitude image"
    tags_dict = {"datatype": "fmap", "suffix": "magnitude1"}
    tags_schema = Magnitude1TagsSchema()


class PhaseDifferenceMagnitude1Step(PhaseDifferenceOnlyMagnitude1Step):
    filetype_str = "first set of magnitude image"
    next_step_type = PhaseDifferenceMagnitude2Step


class PhaseDifferenceMagnitudeTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the type of the magnitude images"
    options = {
        "One magnitude image file": PhaseDifferenceOnlyMagnitude1Step,
        "Two magnitude image files": PhaseDifferenceMagnitude1Step,
    }


class FieldMapMagnitude1Step(PhaseDifferenceMagnitude1Step):
    next_step_type = FieldMapStep


class PEPOLARStep(FilePatternStep):
    filetype_str = "blip-up blip-down EPI image"
    tags_dict = {"datatype": "fmap", "suffix": "epi"}
    allowed_entities = bold_entities
    ask_if_missing_entities = []
    required_in_pattern_entities = ["subject", "direction"]
    next_step_type = BoldDirectionStep
    tags_schema = PEPOLARTagsSchema()


class FmapTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the type of the field maps"
    options = {
        "Blip-up blip-down (PEPOLAR)": PEPOLARStep,
        "Phase difference and magnitude": PhaseDifferenceMagnitudeTypeStep,
        "Field map": FieldMapMagnitude1Step,
    }


class HasFmapStep(YesNoStep):
    header_str = f"Are field-map images available?"
    yes_step_type = FmapTypeStep
    no_step_type = FirstLevelAnalysisStep


FmapStep = HasFmapStep
