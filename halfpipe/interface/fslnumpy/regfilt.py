# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""
import logging

import numpy as np

from nipype.interfaces.base import traits

from ...io import loadmatrix
from ..transformer import Transformer, TransformerInputSpec


def regfilt(array, design, comps, aggressive=False):
    """
    numpy translation of fsl fsl_regfilt.cc dofilter
    """
    zero_based_comps = [c - 1 for c in comps]

    # setup

    data = array
    m, n = data.shape

    mean_r = data.mean(axis=0)
    data -= mean_r[None, :]
    mean_c = design.mean(axis=0)
    design -= mean_c[None, :]

    logging.getLogger("halfpipe").info(f"Data matrix size : {m} x {n}")

    # dofilter

    logging.getLogger("halfpipe").info(f"Calculating maps")

    unmix_matrix = np.linalg.pinv(design)
    maps = unmix_matrix @ data

    noisedes = design[:, zero_based_comps]
    noisemaps = maps[zero_based_comps, :].T

    logging.getLogger("halfpipe").info(f"Calculating filtered data")

    if aggressive:
        new_data = data - noisedes @ (np.linalg.pinv(noisedes) @ data)
    else:
        new_data = data - noisedes @ noisemaps.T

    new_data += mean_r[None, :]

    temp_vol = new_data

    return temp_vol


class FilterRegressorInputSpec(TransformerInputSpec):
    design_file = traits.File(desc="design file", exists=True, mandatory=True)
    filter_columns = traits.List(traits.Int)
    filter_all = traits.Bool(default=False, usedefault=True)
    mask = traits.File(desc="mask image file name", exists=True)
    aggressive = traits.Bool(default=False, usedefault=True)


class FilterRegressor(Transformer):
    input_spec = FilterRegressorInputSpec

    def _transform(self, array, mask=None):
        design = loadmatrix(self.inputs.design_file, dtype=np.float64)

        filter_all = self.inputs.filter_all

        if filter_all is not True:
            filter_columns = self.inputs.filter_columns

        else:
            filter_columns = list(range(1, design.shape[1] + 1))

        array2 = regfilt(
            array, design, filter_columns, aggressive=self.inputs.aggressive
        )

        return array2
