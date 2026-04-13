# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from pathlib import Path

import numpy as np
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec

from ..xdf import xdf
from .connectivity import savetxt_argdict


class XDFInputSpec(TraitedSpec):
    time_series = File(desc="Numpy text file with the timeseries matrix", exists=True, mandatory=True)


class XDFOutputSpec(TraitedSpec):
    effect = File(desc="Numpy text file with Fisher z-transformed correlation matrix")
    variance = File(desc="Numpy text file with the squared standard error of the correlation matrix elements")


class XDF(SimpleInterface):
    input_spec = XDFInputSpec
    output_spec = XDFOutputSpec

    def _run_interface(self, runtime):
        time_series = np.loadtxt(self.inputs.time_series)
        effect, variance = xdf(time_series.transpose())

        effect_path = Path("effect.tsv").resolve()
        np.savetxt(effect_path, effect, **savetxt_argdict)
        self._results["effect"] = effect_path

        variance_path = Path("variance.tsv").resolve()
        np.savetxt(variance_path, variance, **savetxt_argdict)
        self._results["variance"] = variance_path

        return runtime
