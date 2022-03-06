# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional, Type

from ...model import BoldFileSchema
from ..components import (
    MultiCombinedNumberAndSingleChoiceInputView,
    SpacerView,
    TextView,
)
from ..metadata import CheckMetadataStep
from ..pattern import FilePatternStep, FilePatternSummaryStep
from ..step import Step, YesNoStep
from .fmap import FmapStep, FmapSummaryStep

filetype_str = "BOLD image"
filedict = {"datatype": "func", "suffix": "bold"}
schema = BoldFileSchema


def get_post_func_steps(this_next_step_type: Optional[Type[Step]]) -> Type[Step]:
    # class DoReconAllStep(YesNoStep):
    #     header_str = "Do cortical surface-based processing?"
    #     yes_step_type = next_step_type
    #     no_step_type = next_step_type

    #     def next(self, ctx):
    #         if self.choice == "Yes":
    #             ctx.spec.global_settings["run_reconall"] = True
    #         else:
    #             ctx.spec.global_settings["run_reconall"] = False
    #         return super().next(ctx)

    class DummyScansStep(Step):
        detect_str = "Detect non-steady-state via algorithm"

        next_step_type: Optional[Type[Step]] = this_next_step_type

        def setup(self, _):
            self.result = None

            self._append_view(TextView("Remove initial volumes from scans?"))

            self.input_view = MultiCombinedNumberAndSingleChoiceInputView(
                [""],
                [self.detect_str],
                initial_values=[0],
                min=0,
            )

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

        def run(self, _):
            self.result = self.input_view()
            return self.result is not None

        def next(self, ctx):
            if self.result is not None:
                value = next(iter(self.result.values()))
                if isinstance(value, (int, float)):
                    ctx.spec.global_settings["dummy_scans"] = int(value)
                elif value == self.detect_str:
                    ctx.spec.global_settings["dummy_scans"] = None
                else:
                    raise ValueError(f'Unknown dummy_scans value "{value}"')

            if self.next_step_type is not None:
                return self.next_step_type(self.app)(ctx)
            else:
                return ctx

    class CheckBoldSliceTimingStep(CheckMetadataStep):
        schema = BoldFileSchema

        key = "slice_timing"
        filters = filedict

        next_step_type = DummyScansStep

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
        no_step_type = DummyScansStep

        def next(self, ctx):
            if self.choice == "Yes":
                ctx.spec.global_settings["slice_timing"] = True
            else:
                ctx.spec.global_settings["slice_timing"] = False
            return super().next(ctx)

    return DoSliceTimingStep


class BoldSummaryStep(FilePatternSummaryStep):
    filetype_str = filetype_str
    filedict = filedict
    schema = schema

    next_step_type = get_post_func_steps(FmapSummaryStep)


class HasMoreBoldStep(YesNoStep):
    header_str = f"Add more {filetype_str} files?"
    no_step_type = get_post_func_steps(FmapStep)


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
