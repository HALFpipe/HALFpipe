# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from nipype.interfaces.base import isdefined, traits
from numba import guvectorize
from numpy import typing as npt

from ..array_transform import ArrayTransform, ArrayTransformInputSpec


@guvectorize(
    ["void(float64[:], float64[:])"],
    "(n)->()",
    nopython=True,
)
def tsnr(array: npt.NDArray[np.float64], tsnr: npt.NDArray[np.float64]) -> None:
    array = np.nan_to_num(array, copy=False)

    mean = array.mean()
    standard_deviation = np.sqrt(np.square(array - mean).mean())

    if standard_deviation < 1e-3:
        tsnr[0] = 0.0
    else:
        tsnr[0] = mean / standard_deviation


class TSNRInputSpec(ArrayTransformInputSpec):
    dummy_scans = traits.Int(default=0, usedefault=True)


class TSNR(ArrayTransform):
    input_spec = TSNRInputSpec
    suffix = "tsnr"

    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        if isdefined(self.inputs.dummy_scans):
            array = array[self.inputs.dummy_scans :, ...]

        array = tsnr(array.transpose()).transpose()

        # Ensure we have a two-dimensional array
        array = array[np.newaxis, :]

        return array
