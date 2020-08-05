# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import traits, TraitedSpec, SimpleInterface, isdefined, Bunch

from ..io import parse_condition_file


class ParseConditionFileInputSpec(TraitedSpec):
    in_any = traits.Either(
        traits.File(),
        traits.List(traits.File()),
        traits.List(traits.Tuple(traits.Str(), traits.File())),
    )
    condition_names = traits.List(traits.Str(), desc="filter conditions")


class ParseConditionFileOutputSpec(TraitedSpec):
    subject_info = traits.Any()


class ParseConditionFile(SimpleInterface):
    """ interface to construct a group design """

    input_spec = ParseConditionFileInputSpec
    output_spec = ParseConditionFileOutputSpec

    def _run_interface(self, runtime):
        conditions, onsets, durations = parse_condition_file(in_any=self.inputs.in_any)

        if isdefined(self.inputs.condition_names):
            conditions_selected = self.inputs.condition_names
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

        self._results["subject_info"] = Bunch(
            conditions=conditions, onsets=onsets, durations=durations
        )

        return runtime
