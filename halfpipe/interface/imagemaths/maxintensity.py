# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import numpy as np

from ..transformer import Transformer


class MaxIntensity(Transformer):

    def _transform(self, array):
        mask = np.logical_not(np.all(np.isclose(array, 0, atol=1e-5, rtol=1e-3), axis=1))

        argmax = np.argmax(array, axis=1)

        m, n = array.shape
        array2 = np.zeros((m, 1), dtype=array.dtype)
        array2[mask] = argmax[mask, None] + 1

        return array2
