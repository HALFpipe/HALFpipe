# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose

from nipype.interfaces.base import traits, TraitedSpec, SimpleInterface, isdefined, Bunch, File

from ..io import parse_condition_file


class ParseConditionFileInputSpec(TraitedSpec):
    in_any = traits.Either(
        File(),
        traits.List(File()),
        traits.List(traits.Tuple(traits.Str(), File())),
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
    """ interface to construct a group design """

    input_spec = ParseConditionFileInputSpec
    output_spec = ParseConditionFileOutputSpec

    def _run_interface(self, runtime):
        conditions, onsets, durations = parse_condition_file(in_any=self.inputs.in_any)

        if isdefined(self.inputs.condition_names):
            conditions_selected = [str(name) for name in self.inputs.condition_names]  # need a traits-free representation for bunch
            onsets_selected, durations_selected = [], []
            for condition_name in conditions_selected:
                if condition_name not in conditions:
                    condition_onsets = []
                    condition_durations = []
                else:
                    i = conditions.index(condition_name)
                    condition_onsets = onsets[i]
                    condition_durations = durations[i]
                onsets_selected.append(condition_onsets)
                durations_selected.append(condition_durations)
            conditions, onsets, durations = conditions_selected, onsets_selected, durations_selected

        filtered_conditions = [  # filter conditions with zero events
            (condition, onset, duration)
            for condition, onset, duration in zip(conditions, onsets, durations)
            if len(onset) == len(duration) and len(onset) > 0
        ]

        assert len(filtered_conditions) > 0, "No events found"

        conditions, onsets, durations = zip(*filtered_conditions)

        self._results["condition_names"] = list(conditions)

        if isdefined(self.inputs.contrasts):  # filter contrasts based on parsed conditions
            contrasts = self.inputs.contrasts

            newcontrasts = list()
            self._results["contrasts"] = newcontrasts

            for name, type, contrast_conditions, contrast_values in contrasts:
                if any(
                    c not in conditions and not isclose(v, 0)
                    for c, v in zip(contrast_conditions, contrast_values)
                ):
                    continue  # cannot use this contrast

                contrast_conditions, contrast_values = zip(
                    *[
                        (c, v)
                        for c, v in zip(contrast_conditions, contrast_values)
                        if c in conditions
                    ]
                )
                newcontrasts.append(
                    (name, type, list(contrast_conditions), list(contrast_values))
                )

            self._results["contrast_names"] = [
                name for name, _, _, _ in newcontrasts
            ]

        self._results["subject_info"] = Bunch(
            conditions=conditions, onsets=onsets, durations=durations
        )

        return runtime
