# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from numpy import typing as npt

from ..array_transform import ArrayTransform


class ZScore(ArrayTransform):
    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        mean = np.nanmean(array).item()
        std = np.nanstd(array).item()

        if np.isclose(std, 0.0):
            std = 1.0

        np.subtract(array, mean, out=array)
        np.true_divide(array, std, out=array)

        return array
