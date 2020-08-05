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


class CalcMeanOutputSpec(TraitedSpec):
    mean = traits.Either(traits.Float(), traits.List(traits.Float))


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
        return runtime


class ValsInputSpec(TraitedSpec):
    confounds = File(exists=True)
    aroma_metadata = traits.Dict(traits.Str(), traits.Any(), exists=True)


class ValsOutputSpec(TraitedSpec):
    fd_mean = traits.Float()
    fd_perc = traits.Float()
    aroma_noise_frac = traits.Float()


class Vals(SimpleInterface):
    input_spec = ValsInputSpec
    output_spec = ValsOutputSpec

    def _run_interface(self, runtime):
        if isdefined(self.inputs.confounds):
            df_confounds = loadspreadsheet(self.inputs.confounds)
            self._results["fd_mean"] = df_confounds["framewise_displacement"].mean()
            self._results["fd_perc"] = (df_confounds["framewise_displacement"] > 0.2).mean()

        if isdefined(self.inputs.aroma_metadata):
            aroma_metadata = self.inputs.aroma_metadata
            self._results["aroma_noise_frac"] = np.asarray(
                [val["MotionNoise"] is True for val in aroma_metadata.values()]
            ).mean()

        return runtime
