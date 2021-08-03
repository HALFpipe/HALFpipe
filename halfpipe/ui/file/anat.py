# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from ..step import YesNoStep
from ..pattern import FilePatternStep, FilePatternSummaryStep
from .func import FuncStep, FuncSummaryStep

from ...model import T1wFileSchema

filetype_str = "T1-weighted image"
filedict = {"datatype": "anat", "suffix": "T1w"}
schema = T1wFileSchema

next_step_type = FuncStep


class AnatSummaryStep(FilePatternSummaryStep):
    filetype_str = filetype_str
    filedict = filedict
    schema = schema

    next_step_type = FuncSummaryStep


class LesionMaskStep(FilePatternStep):
    filetype_str = "lesion mask"
    filedict = {"datatype": "anat", "label": "lesion", "suffix": "roi"}

    schema = None

    next_step_type = next_step_type


class HasLesionMaskStep(YesNoStep):
    header_str = "Are lesion masks available?"

    yes_step_type = LesionMaskStep
    no_step_type = next_step_type


class AnatStep(FilePatternStep):
    header_str = "Specify anatomical/structural data"

    filetype_str = filetype_str
    filedict = filedict
    schema = schema

    required_in_path_entities = ["subject"]

    next_step_type = HasLesionMaskStep
