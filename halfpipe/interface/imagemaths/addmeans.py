# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from nipype.interfaces.base import traits

from ..transformer import Transformer, TransformerInputSpec


class AddMeansInputSpec(TransformerInputSpec):
    mean_file = traits.File(exists=True, mandatory=True)


class AddMeans(Transformer):
    input_spec = AddMeansInputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_file
        mean_file = self.inputs.mean_file

        mean_data = self._load(mean_file)
        mean_r = mean_data.mean(axis=1)

        array = self._load(in_file)
        array2 = array + mean_r[:, None]

        self._dump(array2)

        return runtime
