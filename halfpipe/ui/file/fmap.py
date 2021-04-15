# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

from operator import attrgetter
from itertools import product

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
    entities,
    entity_longnames,
)
from ..feature import FeaturesStep
from ..step import (
    Step,
    StepType,
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

    next_step_type: StepType = next_step_type


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

        fmapfilepaths = ctx.database.get(**filedict)
        fmaptags = sorted(set(
            frozenset(
                (k, v)
                for k, v in ctx.database.tags(f).items()
                if k not in ["sub", "dir"] and k in entities and v is not None
            )
            for f in fmapfilepaths
        ))
        self.fmaptags = fmaptags

        boldfilepaths = ctx.database.get(**bold_filedict)
        boldtags = sorted(set(
            frozenset(
                (k, v)
                for k, v in ctx.database.tags(f).items()
                if k not in ["sub"] and k in entities and v is not None
            )
            for f in boldfilepaths
        ))
        self.boldtags = boldtags

        if len(fmaptags) > 0:
            def _format_tags(tagset):
                tagdict = dict(tagset)
                return ", ".join(
                    f'{e} "{tagdict[e]}"' if e not in entity_longnames
                    else f'{entity_longnames[e]} "{tagdict[e]}"'
                    for e in entities
                    if e in tagdict and tagdict[e] is not None
                )

            self.is_predefined = False
            self._append_view(TextView("Assign field maps to functional images"))

            self.options = [_format_tags(t).capitalize() for t in boldtags]
            self.values = [f"Field map {_format_tags(t)}".strip() for t in fmaptags]
            selected_indices = [
                self.fmaptags.index(o) if o in fmaptags else 0
                for o in boldtags
            ]

            self.input_view = MultiSingleChoiceInputView(
                [*self.options], [*self.values], selectedIndices=selected_indices
            )
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
            bold_fmap_tag_dict = {
                boldtagset:
                self.fmaptags[
                    self.values.index(self.result[option])
                ]
                for option, boldtagset in zip(self.options, self.boldtags)
            }

            fmap_bold_tag_dict = dict()
            for boldtagset, fmaptagset in bold_fmap_tag_dict.items():
                if fmaptagset not in fmap_bold_tag_dict:
                    fmap_bold_tag_dict[fmaptagset] = boldtagset
                else:
                    fmap_bold_tag_dict[fmaptagset] = fmap_bold_tag_dict[fmaptagset] | boldtagset

            for specfileobj in ctx.spec.files:
                if specfileobj.datatype != "fmap":
                    continue

                fmaplist = ctx.database.resolved_spec.fileobjs_by_specfilepaths[
                    specfileobj.path
                ]

                fmaptags = set(
                    frozenset(
                        (k, v)
                        for k, v in ctx.database.tags(f).items()
                        if k not in ["sub"] and k in entities and v is not None
                    )
                    for f in map(attrgetter("path"), fmaplist)
                )

                def _expand_fmaptags(tagset):
                    if any(a == "acq" for a, _ in tagset):
                        return tagset
                    else:
                        return tagset | frozenset([("acq", "null")])

                mappings = set(
                    (a, b)
                    for fmap in fmaptags
                    for a, b in product(
                        fmap_bold_tag_dict.get(fmap, list()),
                        _expand_fmaptags(fmap),
                    )
                    if a[0] != b[0]
                    and "sub" not in (a[0], b[0])
                )

                intended_for = dict()
                for functag, fmaptag in mappings:
                    entity, val = functag
                    funcstr = f"{entity}.{val}"
                    entity, val = fmaptag
                    fmapstr = f"{entity}.{val}"
                    if fmapstr not in intended_for:
                        intended_for[fmapstr] = list()
                    intended_for[fmapstr].append(funcstr)

                specfileobj.intended_for = intended_for

        if self.is_first_run or not self.is_predefined:
            self.is_first_run = False
            return CheckBoldEffectiveEchoSpacingStep(self.app)(ctx)


class HasMoreFmapStep(YesNoStep):
    header_str = "Add more field maps?"
    yes_step_type: Optional[StepType] = None  # add later, because not yet defined
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

        next_step_type = m_next_step_type

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
    header_str = "Specify field maps?"
    yes_step_type = FmapTypeStep
    no_step_type = next_step_type


HasMoreFmapStep.yes_step_type = FmapTypeStep

FmapStep = HasFmapStep
