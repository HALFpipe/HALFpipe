# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose

from nipype.interfaces.base import (
    Bunch,
    SimpleInterface,
    TraitedSpec,
    isdefined,
    traits,
)

from ..ingest.events import ConditionFile
from ..logging import logger


class ApplyConditionOffsetInputSpec(TraitedSpec):
    subject_info = traits.Any()
    scan_start = traits.Float()


class ApplyConditionOffsetOutputSpec(TraitedSpec):
    subject_info = traits.Any()


class ApplyConditionOffset(SimpleInterface):
    input_spec = ApplyConditionOffsetInputSpec
    output_spec = ApplyConditionOffsetOutputSpec

    def _run_interface(self, runtime):
        subject_info = self.inputs.subject_info
        scan_start = self.inputs.scan_start

        conditions = subject_info.conditions
        onsets = subject_info.onsets
        durations = subject_info.durations

        for condition, condition_onsets in zip(conditions, onsets, strict=False):
            for i, onset in enumerate(condition_onsets):
                onset -= scan_start
                if onset < 0:
                    logger.warning(f'Condition "{condition}" onset truncated from {onset:f} to {0.0:f} s.')
                    onset = 0
                condition_onsets[i] = onset

        self._results["subject_info"] = Bunch(conditions=conditions, onsets=onsets, durations=durations)

        return runtime


class ParseConditionFileInputSpec(TraitedSpec):
    in_any = traits.Any(
        mandatory=True,
    )

    condition_names = traits.List(traits.Str(), desc="filter conditions")

    contrasts = traits.List(
        traits.Tuple(
            traits.Str,
            traits.Enum("T"),
            traits.List(traits.Str),
            traits.List(traits.Float),
        ),
    )


class ParseConditionFileOutputSpec(TraitedSpec):
    subject_info = traits.Any()

    contrasts = traits.List(
        traits.Tuple(
            traits.Str,
            traits.Enum("T"),
            traits.List(traits.Str),
            traits.List(traits.Float),
        ),
    )

    condition_names = traits.List(traits.Str)
    contrast_names = traits.List(traits.Str)


class ParseConditionFile(SimpleInterface):
    input_spec = ParseConditionFileInputSpec
    output_spec = ParseConditionFileOutputSpec

    def _run_interface(self, runtime):
        # parse input files
        cf = ConditionFile(data=self.inputs.in_any)
        conditions = cf.conditions
        onsets = cf.onsets
        durations = cf.durations

        # use only selected conditions
        if isdefined(self.inputs.condition_names):
            conditions, onsets, durations = cf.select(self.inputs.condition_names)

        # remove empty or invalid conditions
        filtered_conditions = [
            (condition, onset, duration)
            for condition, onset, duration in zip(conditions, onsets, durations, strict=False)
            if len(onset) == len(duration) and len(onset) > 0
        ]
        assert len(filtered_conditions) > 0, "No events found"
        conditions, onsets, durations = map(list, zip(*filtered_conditions, strict=False))

        # filter and re-write contrasts based on available conditions
        if isdefined(self.inputs.contrasts):
            contrasts = self.inputs.contrasts
            new_contrasts = list()
            for name, contrast_type, contrast_conditions, contrast_values in contrasts:
                if any(
                    condition not in conditions  # is missing
                    and not isclose(value, 0)  # but is part of the contrast
                    for condition, value in zip(contrast_conditions, contrast_values, strict=False)
                ):
                    continue

                filtered_contrast = [
                    (condition, value)
                    for condition, value in zip(contrast_conditions, contrast_values, strict=False)
                    if condition in conditions
                ]
                contrast_conditions, contrast_values = map(list, zip(*filtered_contrast, strict=False))

                new_contrasts.append(
                    (
                        name,
                        contrast_type,
                        contrast_conditions,
                        contrast_values,
                    )
                )

            self._results["contrast_names"] = [name for name, _, _, _ in new_contrasts]
            self._results["contrasts"] = new_contrasts

        self._results["condition_names"] = list(conditions)
        self._results["subject_info"] = Bunch(conditions=conditions, onsets=onsets, durations=durations)

        return runtime
