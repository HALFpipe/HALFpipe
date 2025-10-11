# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from nipype.interfaces.base import isdefined, traits
from numpy import typing as npt

from ..array_transform import ArrayTransform, ArrayTransformInputSpec


class TSNRInputSpec(ArrayTransformInputSpec):
    dummy_scans = traits.Int(default=0, usedefault=True)


class TSNR(ArrayTransform):
    input_spec = TSNRInputSpec
    suffix = "tsnr"

    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        if isdefined(self.inputs.dummy_scans):
            array = array[self.inputs.dummy_scans :, ...]

        array = np.nan_to_num(array, copy=False)

        volume_count, _ = array.shape
        mean = array.mean(axis=0)
        np.subtract(array, mean, out=array)
        np.square(array, out=array)
        standard_deviation = np.sqrt(array.sum(axis=0) / volume_count)

        tsnr = np.zeros_like(mean)
        np.true_divide(
            mean,
            standard_deviation,
            out=tsnr,
            where=standard_deviation > 1e-3,
        )

        # Ensure we have a two-dimensional array
        tsnr = tsnr[np.newaxis, :]

        return tsnr
