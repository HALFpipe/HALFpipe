# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from ...model import T1wFileSchema
from ..pattern import FilePatternStep, FilePatternSummaryStep
from .func import FuncStep, FuncSummaryStep

filetype_str = "T1-weighted image"
filedict = {"datatype": "anat", "suffix": "T1w"}
schema = T1wFileSchema


class AnatSummaryStep(FilePatternSummaryStep):
    filetype_str = filetype_str
    filedict = filedict
    schema = schema

    next_step_type = FuncSummaryStep


class AnatStep(FilePatternStep):
    header_str = "Specify anatomical/structural data"

    filetype_str = filetype_str
    filedict = filedict
    schema = schema

    required_in_path_entities = ["subject"]

    next_step_type = FuncStep
