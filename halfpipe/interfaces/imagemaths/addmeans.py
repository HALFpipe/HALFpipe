# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from nipype.interfaces.base import File

from ..transformer import Transformer, TransformerInputSpec


class AddMeansInputSpec(TransformerInputSpec):
    mean_file = File(exists=True, mandatory=True)


class AddMeans(Transformer):
    input_spec = AddMeansInputSpec

    suffix = "addmean"

    def _run_interface(self, runtime):
        in_file = self.inputs.in_file
        mean_file = self.inputs.mean_file

        mean_data = self._load(mean_file)
        mean_r = np.nanmean(mean_data, axis=0)

        array = self._load(in_file)
        array2 = array + mean_r

        out_file = self._dump(array2)
        self._results["out_file"] = out_file

        return runtime
