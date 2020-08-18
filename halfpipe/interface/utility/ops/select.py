# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""
import re

from nipype.interfaces.base import (
    SimpleInterface,
    TraitedSpec,
    traits
)


class SelectInputSpec(TraitedSpec):
    in_list = traits.List(traits.Str(), mandatory=True)
    regex = traits.Str(desc="select file names that match this", mandatory=True)


class SelectOutputSpec(TraitedSpec):
    match_list = traits.List(traits.Str(), mandatory=True)
    match_indices = traits.List(traits.Int())
    other_list = traits.List(traits.Str(), mandatory=True)
    other_indices = traits.List(traits.Int())


class Select(SimpleInterface):
    input_spec = SelectInputSpec
    output_spec = SelectOutputSpec

    def _run_interface(self, runtime):
        in_list = self.inputs.in_list
        regex = re.compile(self.inputs.regex)

        match_list = []
        match_indices = []
        other_list = []
        other_indices = []

        for i, v in enumerate(in_list):
            if regex.fullmatch(v) is not None:
                match_list.append(v)
                match_indices.append(i)
            else:
                other_list.append(v)
                other_indices.append(i)

        self._results["match_list"] = match_list
        self._results["match_indices"] = match_indices
        self._results["other_list"] = other_list
        self._results["other_indices"] = other_indices

        return runtime
