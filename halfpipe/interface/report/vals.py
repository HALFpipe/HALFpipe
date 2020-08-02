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

from ..io import meansignals, loadspreadsheet


class ValsInputSpec(TraitedSpec):
    confounds = File(exists=True)
    tsnr_file = File(exists=True)
    dseg = File(exists=True)
    aroma_metadata = traits.Dict(traits.Str(), traits.Any(), exists=True)


class ValsOutputSpec(TraitedSpec):
    fd_mean = traits.Float()
    fd_perc = traits.Float()
    aroma_noise_frac = traits.Float()
    mean_gm_tsnr = traits.Float()


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

        if isdefined(self.inputs.tsnr_file) and isdefined(self.inputs.dseg):
            _, self._results["mean_gm_tsnr"], _ = meansignals(
                self.inputs.tsnr_file, self.inputs.dseg
            ).ravel()

        return runtime
