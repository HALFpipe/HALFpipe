# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from .pattern import FilePatternStep, FilePatternSummaryStep
from ..spec import BoldTagsSchema, bold_entities
from .utils import YesNoStep
from .fmap import FmapStep, FmapSummaryStep


class BoldSummaryStep(FilePatternSummaryStep):
    filetype_str = "BOLD image"
    tags_dict = {"datatype": "func", "suffix": "bold"}
    allowed_entities = ["subject", "session", "run", "task"]
    next_step_type = FmapSummaryStep


class HasMoreBoldStep(YesNoStep):
    header_str = "Add more BOLD image files?"
    yes_step_type = None  # add later, because not yet defined
    no_step_type = FmapStep


class BoldStep(FilePatternStep):
    header_str = "Specify functional data"
    filetype_str = "BOLD image"
    tags_dict = {"datatype": "func", "suffix": "bold"}
    allowed_entities = bold_entities
    ask_if_missing_entities = ["task"]
    required_in_pattern_entities = ["subject"]
    next_step_type = HasMoreBoldStep
    tags_schema = BoldTagsSchema()

    def setup(self, ctx):
        super(BoldStep, self).setup(ctx)
        self.next_step_type = HasMoreBoldStep


HasMoreBoldStep.yes_step_type = BoldStep
FuncStep = BoldStep
FuncSummaryStep = BoldSummaryStep
