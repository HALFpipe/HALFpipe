# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File,
    isdefined,
)

from ...utils import first
from ...io import meansignals, loadspreadsheet


class CalcMeanInputSpec(TraitedSpec):
    in_file = File(exists=True, mandatory=True)
    mask = File(exists=True)
    parcellation = File(exists=True)
    dseg = File(exists=True)

    vals = traits.Dict(traits.Str(), traits.Any())
    key = traits.Str()


class CalcMeanOutputSpec(TraitedSpec):
    mean = traits.Either(traits.Float(), traits.List(traits.Float))
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
            _, self._results["mean"], _ = meansignals(
                in_file, self.inputs.dseg, mask_file=mask_file, min_n_voxels=0
            ).ravel()
        elif isdefined(self.inputs.parcellation):
            self._results["mean"] = meansignals(
                in_file, self.inputs.parcellation, mask_file=mask_file, min_n_voxels=0
            ).ravel()
        elif mask_file is not None:
            self._results["mean"] = first(meansignals(
                in_file, mask_file, min_n_voxels=0
            ).ravel())
        vals = dict()
        self._results["vals"] = vals
        if isdefined(self.inputs.vals):
            vals.update(self.inputs.vals)
        if isdefined(self.inputs.key):
            vals[self.inputs.key] = self._results["mean"]
        return runtime


class ValsInputSpec(TraitedSpec):
    vals = traits.Dict(traits.Str(), traits.Any())
    confounds = File(exists=True)
    aroma_metadata = traits.Dict(traits.Str(), traits.Any(), exists=True)
    fd_thres = traits.Float()
    dummy = traits.Int()


class ValsOutputSpec(TraitedSpec):
    vals = traits.Dict(traits.Str(), traits.Any())


class Vals(SimpleInterface):
    input_spec = ValsInputSpec
    output_spec = ValsOutputSpec

    def _run_interface(self, runtime):
        vals = dict()
        self._results["vals"] = vals
        if isdefined(self.inputs.vals):
            vals.update(self.inputs.vals)
        if isdefined(self.inputs.confounds):
            df_confounds = loadspreadsheet(self.inputs.confounds)
            vals["fd_mean"] = df_confounds["framewise_displacement"].mean()
            if isdefined(self.inputs.fd_thres):
                vals["fd_perc"] = (df_confounds["framewise_displacement"] > self.inputs.fd_thres).mean()
        if isdefined(self.inputs.aroma_metadata):
            aroma_metadata = self.inputs.aroma_metadata
            vals["aroma_noise_frac"] = np.asarray(
                [val["MotionNoise"] is True for val in aroma_metadata.values()]
            ).mean()
        if isdefined(self.inputs.dummy):
            vals["dummy"] = self.inputs.dummy

        return runtime
