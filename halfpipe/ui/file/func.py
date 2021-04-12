# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

from ...model import BoldFileSchema

from ..pattern import FilePatternStep, FilePatternSummaryStep
from ..step import YesNoStep, StepType
from ..metadata import CheckMetadataStep
from .fmap import FmapStep, FmapSummaryStep

filetype_str = "BOLD image"
filedict = {"datatype": "func", "suffix": "bold"}
schema = BoldFileSchema


def get_slice_timing_steps(next_step_type) -> StepType:
    class CheckBoldSliceTimingStep(CheckMetadataStep):
        schema = BoldFileSchema

        key = "slice_timing"
        filters = filedict

        def __init__(self, app, **kwargs):
            super(CheckBoldSliceTimingStep, self).__init__(app, **kwargs)
            self.next_step_type = next_step_type

        def _should_skip(self, ctx):
            if self.key in ctx.already_checked:
                return True
            ctx.already_checked.add(self.key)
            return False

    class CheckBoldSliceEncodingDirectionStep(CheckMetadataStep):
        schema = BoldFileSchema

        key = "slice_encoding_direction"
        filters = filedict

        next_step_type = CheckBoldSliceTimingStep

        def _should_skip(self, ctx):
            if self.key in ctx.already_checked:
                return True
            ctx.already_checked.add(self.key)
            return False

    class DoSliceTimingStep(YesNoStep):
        header_str = "Do slice timing?"
        yes_step_type = CheckBoldSliceEncodingDirectionStep
        no_step_type = next_step_type

        def next(self, ctx):
            if self.choice == "Yes":
                ctx.spec.global_settings["slice_timing"] = True
            else:
                ctx.spec.global_settings["slice_timing"] = False
            return super(DoSliceTimingStep, self).next(ctx)

    return DoSliceTimingStep


class BoldSummaryStep(FilePatternSummaryStep):
    filetype_str = filetype_str
    filedict = filedict
    schema = schema

    next_step_type = get_slice_timing_steps(FmapSummaryStep)


class HasMoreBoldStep(YesNoStep):
    header_str = f"Add more {filetype_str} files?"
    yes_step_type: Optional[StepType] = None  # add later, because not yet defined
    no_step_type: StepType = get_slice_timing_steps(FmapStep)


class CheckRepetitionTimeStep(CheckMetadataStep):
    schema = schema

    key = "repetition_time"

    next_step_type = HasMoreBoldStep


class BoldStep(FilePatternStep):
    filetype_str = filetype_str
    filedict = filedict
    schema = schema

    ask_if_missing_entities = ["task"]
    required_in_path_entities = ["subject"]

    next_step_type = CheckRepetitionTimeStep


class FirstBoldStep(BoldStep):
    header_str = "Specify functional data"


HasMoreBoldStep.yes_step_type = BoldStep

FuncStep = FirstBoldStep
FuncSummaryStep = BoldSummaryStep
