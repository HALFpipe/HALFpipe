# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from nipype.interfaces.base import isdefined, traits
from numpy import typing as npt

from ..transformer import Transformer, TransformerInputSpec


class TSNRInputSpec(TransformerInputSpec):
    dummy_scans = traits.Int(default=0, usedefault=True)


class TSNR(Transformer):
    input_spec = TSNRInputSpec
    suffix = "tsnr"

    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        if isdefined(self.inputs.dummy_scans):
            array = array[self.inputs.dummy_scans :, ...]

        array = np.nan_to_num(array)

        mean = array.mean(axis=0)
        std = array.std(axis=0)

        _, m = array.shape
        tsnr = np.zeros((m,))

        nonzero = std > 1.0e-3
        tsnr[nonzero] = mean[nonzero] / std[nonzero]

        # ensure we have a two-dimensional array
        tsnr = tsnr[np.newaxis, :]  # type: ignore[assignment]

        return tsnr
