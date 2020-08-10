# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import (
    TextView,
    SpacerView,
    MultiSingleChoiceInputView,
)

from ..pattern import FilePatternStep, FilePatternSummaryStep
from ...model import (
    PhaseFmapFileSchema,
    PhaseDiffFmapFileSchema,
    EPIFmapFileSchema,
    BaseFmapFileSchema,
    BoldFileSchema,
)
from ..feature import FeaturesStep

from ..step import (
    Step,
    BranchStep,
    YesNoStep,
)
from ..metadata import CheckMetadataStep

filetype_str = "field map image"
filedict = {"datatype": "fmap"}

bold_filedict = {"datatype": "func", "suffix": "bold"}

next_step_type = FeaturesStep


class FmapSummaryStep(FilePatternSummaryStep):
    filetype_str = filetype_str
    filedict = filedict
    schema = BaseFmapFileSchema

    next_step_type = next_step_type


class CheckBoldPhaseEncodingDirectionStep(CheckMetadataStep):
    schema = BoldFileSchema

    key = "phase_encoding_direction"
    appendstr = " for the functional data"
    filters = bold_filedict

    next_step_type = next_step_type


class CheckBoldEffectiveEchoSpacingStep(CheckMetadataStep):
    schema = BoldFileSchema

    key = "effective_echo_spacing"
    appendstr = " for the functional data"
    filters = bold_filedict

    next_step_type = CheckBoldPhaseEncodingDirectionStep

    def _should_skip(self, ctx):
        filepaths = [*ctx.database.get(**filedict)]
        suffixvalset = ctx.database.tagvalset("suffix", filepaths=filepaths)
        return suffixvalset.isdisjoint(["phase1", "phase2", "phasediff", "fieldmap"])


class AcqToTaskMappingStep(Step):
    def setup(self, ctx):
        self.is_first_run = True

        self.result = None

        filepaths = ctx.database.get(**filedict)
        boldfilepaths = ctx.database.get(**bold_filedict)

        acqvalset = ctx.database.tagvalset("acq", filepaths=filepaths)
        fmaptaskvalset = ctx.database.tagvalset("task", filepaths=filepaths)

        taskvalset = ctx.database.tagvalset("task", filepaths=boldfilepaths)

        if (
            acqvalset is not None
            and len(acqvalset) > 0
            and (fmaptaskvalset is None or len(fmaptaskvalset) == 0)
        ):
            if None in acqvalset:
                acqvalset.remove(None)
            self.acqvals = sorted(list(acqvalset))

            if None in fmaptaskvalset:
                fmaptaskvalset.remove(None)

            if None in taskvalset:
                taskvalset.remove(None)
            self.taskvals = sorted(list(taskvalset))

            self.is_predefined = False
            self._append_view(TextView(f"Found {len(self.acqvals)} field map acquisitions"))
            self._append_view(TextView("Assign field maps to tasks"))

            self.options = [f'"{taskval}"' for taskval in self.taskvals]
            self.values = [f"{acqval}" for acqval in self.acqvals]

            self.input_view = MultiSingleChoiceInputView([*self.options], [*self.values])
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

        else:
            self.is_predefined = True

    def run(self, ctx):
        if self.is_predefined:
            return self.is_first_run
        else:
            self.result = self.input_view()
            if self.result is None:
                return False
            return True

    def next(self, ctx):
        if self.result is not None:
            filepaths = ctx.database.get(**filedict)

            specfileobjs = set(ctx.database.specfileobj(filepath) for filepath in filepaths)

            acq_by_value = dict(zip(self.values, self.acqvals))

            value = dict()
            for option, task in zip(self.options, self.taskvals):
                acq = acq_by_value[self.result[option]]
                key = f"acq.{acq}"
                if key not in value:
                    value[key] = []
                value[key].append(f"task.{task}")

            for specfileobj in specfileobjs:
                specfileobj.intended_for = value

        if self.is_first_run or not self.is_predefined:
            self.is_first_run = False
            return CheckBoldEffectiveEchoSpacingStep(self.app)(ctx)


class HasMoreFmapStep(YesNoStep):
    header_str = f"Add more field maps?"
    yes_step_type = None  # add later, because not yet defined
    no_step_type = AcqToTaskMappingStep


class FieldMapStep(FilePatternStep):
    filetype_str = "field map image"
    filedict = {**filedict, "suffix": "fieldmap"}
    schema = BaseFmapFileSchema

    required_in_path_entities = ["subject"]

    next_step_type = HasMoreFmapStep


class CheckPhaseDiffEchoTimeDiffStep(CheckMetadataStep):
    schema = PhaseDiffFmapFileSchema
    key = "echo_time_difference"
    next_step_type = HasMoreFmapStep


class PhaseDiffStep(FilePatternStep):
    filetype_str = "phase difference image"
    filedict = {**filedict, "suffix": "phasediff"}
    schema = PhaseDiffFmapFileSchema

    required_in_path_entities = ["subject"]

    next_step_type = CheckPhaseDiffEchoTimeDiffStep


class CheckPhase2EchoTimeStep(CheckMetadataStep):
    schema = PhaseFmapFileSchema
    key = "echo_time"
    next_step_type = HasMoreFmapStep


class Phase2Step(FilePatternStep):
    filetype_str = "second set of phase image"
    filedict = {**filedict, "suffix": "phase2"}
    schema = PhaseFmapFileSchema

    required_in_path_entities = ["subject"]

    next_step_type = CheckPhase2EchoTimeStep


class CheckPhase1EchoTimeStep(CheckMetadataStep):
    schema = PhaseFmapFileSchema
    key = "echo_time"
    next_step_type = Phase2Step


class Phase1Step(FilePatternStep):
    filetype_str = "first set of phase image"
    filedict = {**filedict, "suffix": "phase1"}
    schema = PhaseFmapFileSchema

    required_in_path_entities = ["subject"]

    next_step_type = CheckPhase1EchoTimeStep


class PhaseTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the type of the phase images"
    options = {
        "One phase difference image": PhaseDiffStep,
        "Two phase images": Phase1Step,
    }


def get_magnitude_steps(m_next_step_type):
    class Magnitude2Step(FilePatternStep):
        filetype_str = "second set of magnitude image"
        filedict = {**filedict, "suffix": "magnitude2"}
        schema = BaseFmapFileSchema

        required_in_path_entities = ["subject"]

        next_step_type = m_next_step_type

    class Magnitude1Step(Magnitude2Step):
        filetype_str = "first set of magnitude image"
        filedict = {**filedict, "suffix": "magnitude1"}

        next_step_type = Magnitude2Step

    class MagnitudeStep(Magnitude1Step):
        filetype_str = "magnitude image"

    class MagnitudeTypeStep(BranchStep):
        is_vertical = True
        header_str = "Specify the type of the magnitude images"
        options = {
            "One magnitude image file": MagnitudeStep,
            "Two magnitude image files": Magnitude1Step,
        }

    return MagnitudeTypeStep


class EPIStep(FilePatternStep):
    filetype_str = "blip-up blip-down EPI image"
    filedict = {**filedict, "suffix": "epi"}
    schema = EPIFmapFileSchema

    required_in_path_entities = ["subject"]

    next_step_type = HasMoreFmapStep


class FmapTypeStep(BranchStep):
    is_vertical = True
    header_str = "Specify the type of the field maps"
    options = {
        "EPI (blip-up blip-down)": EPIStep,
        "Phase difference and magnitude (used by Siemens scanners)": get_magnitude_steps(
            PhaseTypeStep
        ),
        "Scanner-computed field map and magnitude (used by GE / Philips scanners)": get_magnitude_steps(
            FieldMapStep
        ),
    }


class HasFmapStep(YesNoStep):
    header_str = f"Specify field maps?"
    yes_step_type = FmapTypeStep
    no_step_type = next_step_type


HasMoreFmapStep.yes_step_type = FmapTypeStep

FmapStep = HasFmapStep
