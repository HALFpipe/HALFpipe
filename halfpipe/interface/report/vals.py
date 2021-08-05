# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    DynamicTraitedSpec,
    SimpleInterface,
    File,
    isdefined,
)
from nipype.interfaces.io import add_traits, IOBase

from ...io.parse import loadspreadsheet
from ...io.signals import mean_signals


class CalcMeanInputSpec(TraitedSpec):
    in_file = File(exists=True, mandatory=True)
    mask = File(exists=True)
    parcellation = File(exists=True)
    dseg = File(exists=True)

    vals = traits.Dict(traits.Str(), traits.Any())
    key = traits.Str()


class CalcMeanOutputSpec(TraitedSpec):
    mean = traits.Either(traits.Float(), traits.List(traits.Float()))
    vals = traits.Dict(traits.Str(), traits.Any())


class CalcMean(SimpleInterface):
    input_spec = CalcMeanInputSpec
    output_spec = CalcMeanOutputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_file
        mask_file = None
        if isdefined(self.inputs.mask):
            mask_file = self.inputs.mask

        if isdefined(self.inputs.dseg):  # get grey matter only
            _, self._results["mean"], _ = np.ravel(
                mean_signals(in_file, self.inputs.dseg, mask_file=mask_file)
            )
        elif isdefined(self.inputs.parcellation):
            self._results["mean"] = list(
                np.ravel(
                    mean_signals(in_file, self.inputs.parcellation, mask_file=mask_file)
                )
            )
        elif mask_file is not None:
            mean = mean_signals(in_file, mask_file)
            self._results["mean"] = float(mean[0])
        vals = dict()
        self._results["vals"] = vals
        if isdefined(self.inputs.vals):
            vals.update(self.inputs.vals)
        if isdefined(self.inputs.key):
            vals[self.inputs.key] = self._results["mean"]
        return runtime


class UpdateValsInputSpec(DynamicTraitedSpec):
    vals = traits.Dict(traits.Str(), traits.Any())
    confounds = File(exists=True)
    aroma_metadata = traits.Dict(traits.Str(), traits.Any(), exists=True)
    fd_thres = traits.Float()


class UpdateValsOutputSpec(TraitedSpec):
    vals = traits.Dict(traits.Str(), traits.Any())


class UpdateVals(IOBase):
    input_spec = UpdateValsInputSpec
    output_spec = UpdateValsOutputSpec

    def __init__(self, fields=[], **inputs):
        super().__init__(**inputs)

        self.fields = fields
        add_traits(self.inputs, [*self.fields])

    def _list_outputs(self):
        outputs = self._outputs()
        assert outputs is not None
        outputs = outputs.get()

        vals = dict()

        if isdefined(self.inputs.vals):
            vals.update(self.inputs.vals)

        if isdefined(self.inputs.confounds):
            confounds = loadspreadsheet(self.inputs.confounds)
            fd = confounds["framewise_displacement"]

            vals["fd_mean"] = fd.mean()

            if isdefined(self.inputs.fd_thres):
                vals["fd_perc"] = (fd > self.inputs.fd_thres).mean()

        if isdefined(self.inputs.aroma_metadata):
            aroma_metadata = self.inputs.aroma_metadata
            is_noise_component = [c["MotionNoise"] is True for c in aroma_metadata.values()]
            vals["aroma_noise_frac"] = np.array(is_noise_component).astype(float).mean()

        for field in self.fields:
            value = getattr(self.inputs, field, None)
            if isdefined(value):
                vals[field] = value

        outputs["vals"] = vals

        return outputs
