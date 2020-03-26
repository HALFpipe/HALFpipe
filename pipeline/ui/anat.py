# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from .pattern import FilePatternStep, FilePatternSummaryStep
from ..spec import AnatTagsSchema
from .func import FuncStep, FuncSummaryStep


class AnatSummaryStep(FilePatternSummaryStep):
    filetype_str = "T1-weighted image"
    tags_dict = {"datatype": "anat", "suffix": "T1w"}
    allowed_entities = ["subject"]
    next_step_type = FuncSummaryStep


class AnatStep(FilePatternStep):
    header_str = "Specify anatomical/structural data"
    filetype_str = "T1-weighted image"
    tags_dict = {"datatype": "anat", "suffix": "T1w"}
    allowed_entities = ["subject"]
    ask_if_missing_entities = []
    required_in_pattern_entities = ["subject"]
    next_step_type = FuncStep
    tags_schema = AnatTagsSchema()
