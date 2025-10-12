# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from numpy import typing as npt

from ..array_transform import ArrayTransform


class MaxIntensity(ArrayTransform):
    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        mask = np.logical_not(np.all(np.isclose(array, 0, atol=1e-5, rtol=1e-3), axis=0))

        argmax = np.argmax(array, axis=0)

        _, voxel_count = array.shape

        array2 = np.zeros((1, voxel_count), dtype=array.dtype)
        array2[:, mask] = argmax[mask] + 1

        return array2
