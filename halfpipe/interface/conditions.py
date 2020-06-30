# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import traits, TraitedSpec, SimpleInterface
from nipype.interfaces.base import Bunch

from ..io import parse_condition_file


class ParseConditionFileInputSpec(TraitedSpec):
    in_any = traits.Either(
        traits.File(),
        traits.List(traits.File()),
        traits.List(traits.Tuple(traits.Str(), traits.File())),
    )


class ParseConditionFileOutputSpec(TraitedSpec):
    subject_info = traits.Any()


class ParseConditionFile(SimpleInterface):
    """ interface to construct a group design """

    input_spec = ParseConditionFileInputSpec
    output_spec = ParseConditionFileOutputSpec

    def _run_interface(self, runtime):
        conditions, onsets, durations = parse_condition_file(in_any=self.inputs.in_any)

        self._results["subject_info"] = Bunch(
            conditions=conditions, onsets=onsets, durations=durations
        )

        return runtime
