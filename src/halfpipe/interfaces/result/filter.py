# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from nipype.interfaces.base import (
    BaseInterfaceInputSpec,
    File,
    SimpleInterface,
    isdefined,
    traits,
)
from nipype.interfaces.base.support import Bunch

from ...result.base import ResultDict
from ...result.filter import filter_results
from .base import ResultdictsOutputSpec


class FilterResultdictsInputSpec(BaseInterfaceInputSpec):
    in_dicts = traits.List(traits.Dict(traits.Str(), traits.Any()), mandatory=True)

    model_name = traits.Str()
    filter_dicts = traits.List(traits.Any(), desc="filter list")
    variable_dicts = traits.List(traits.Any(), desc="variable list")
    spreadsheet = File(desc="spreadsheet", exists=True)
    require_one_of_images = traits.List(traits.Str(), desc="only keep resultdicts that have at least one of these keys")
    exclude_files = traits.List(traits.Str())


class FilterResultdicts(SimpleInterface):
    input_spec = FilterResultdictsInputSpec
    output_spec = ResultdictsOutputSpec

    def _run_interface(self, runtime: Bunch) -> Bunch:
        out_dicts: list[ResultDict] = self.inputs.in_dicts.copy()

        variable_dicts: list[dict] | None = None
        if isdefined(self.inputs.variable_dicts):
            variable_dicts = self.inputs.variable_dicts

        spreadsheet: Path | str | None = None
        if isdefined(self.inputs.spreadsheet):
            spreadsheet = self.inputs.spreadsheet

        model_name: str | None = None
        if isdefined(self.inputs.model_name):
            model_name = self.inputs.model_name

        filter_dicts: list[dict] = list()
        if isdefined(self.inputs.filter_dicts):
            filter_dicts.extend(self.inputs.filter_dicts)

        require_one_of_images: list[str] = list()
        if isdefined(self.inputs.require_one_of_images):
            require_one_of_images = self.inputs.require_one_of_images

        exclude_files: list[str] | None = None
        if isdefined(self.inputs.exclude_files):
            exclude_files = self.inputs.exclude_files

        out_dicts = filter_results(
            out_dicts,
            filter_dicts,
            spreadsheet,
            variable_dicts,
            model_name,
            require_one_of_images,
            exclude_files,
        )

        self._results["resultdicts"] = out_dicts

        return runtime
