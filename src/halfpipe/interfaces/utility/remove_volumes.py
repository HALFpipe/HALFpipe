# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from nipype.interfaces.base import traits
from numpy import typing as npt

from ..transformer import Transformer, TransformerInputSpec


class RemoveVolumesInputSpec(TransformerInputSpec):
    count = traits.Int(mandatory=True)


class RemoveVolumes(Transformer):
    input_spec = RemoveVolumesInputSpec
    suffix = "cut"

    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        array2 = array[self.inputs.count :, ...]
        return array2
