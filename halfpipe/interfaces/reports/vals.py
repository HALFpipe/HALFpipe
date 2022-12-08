# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
import pandas as pd
from nipype.interfaces.base import (
    DynamicTraitedSpec,
    File,
    SimpleInterface,
    TraitedSpec,
    isdefined,
    traits,
)
from nipype.interfaces.io import IOBase, add_traits

from ..connectivity import mean_signals


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
            dseg_mean_signals = mean_signals(
                in_file, self.inputs.dseg, mask_file=mask_file
            )
            _, gm_mean, _ = np.ravel(dseg_mean_signals).tolist()
            self._results["mean"] = float(gm_mean)

        elif isdefined(self.inputs.parcellation):
            parc_mean_signals = mean_signals(
                in_file, self.inputs.parcellation, mask_file=mask_file
            )
            parc_mean_signals_list = list(
                map(float, np.ravel(parc_mean_signals).tolist())
            )
            self._results["mean"] = parc_mean_signals_list

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
    confounds_file = File(exists=True)
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

        confounds_file = self.inputs.confounds_file
        if isdefined(confounds_file):

            data_frame = pd.read_csv(
                confounds_file,
                sep="\t",
                index_col=None,
                dtype=np.float64,
                na_filter=True,
                na_values="n/a",
            )
            assert isinstance(data_frame, pd.DataFrame)

            fd = data_frame["framewise_displacement"]
            fd.fillna(value=0.0, inplace=True)

            vals["fd_mean"] = float(fd.mean())

            if isdefined(self.inputs.fd_thres):
                fd_prop = float((fd > self.inputs.fd_thres).mean())
                vals["fd_perc"] = fd_prop * 100  # rescale to percent

        if isdefined(self.inputs.aroma_metadata):
            aroma_metadata = self.inputs.aroma_metadata
            is_noise_component = [
                c["MotionNoise"] is True for c in aroma_metadata.values()
            ]
            vals["aroma_noise_frac"] = float(
                np.array(is_noise_component).astype(float).mean()
            )

        for field in self.fields:
            value = getattr(self.inputs, field, None)
            if isdefined(value):
                vals[field] = value

        outputs["vals"] = vals

        return outputs
