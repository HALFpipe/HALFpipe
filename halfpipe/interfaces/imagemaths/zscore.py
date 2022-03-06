# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

from ..transformer import Transformer


class ZScore(Transformer):
    def _transform(self, array):
        mean = np.nanmean(array)
        std = np.nanstd(array)

        if np.isclose(std, 0):
            std = 1

        array2 = (array - mean) / std

        return array2
