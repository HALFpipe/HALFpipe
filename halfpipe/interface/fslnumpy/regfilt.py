# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""
import logging

import numpy as np
import nibabel as nib

from nipype.interfaces.base import (
    traits,
    isdefined,
)

from ..utils import readtsv
from ..transformer import Transformer, TransformerInputSpec


def binarise(array, lowerth, upperth, threstype="inclusive", invert=False):
    """
    numpy translation of fsl newimage.cc binarise
    default arguments come from newimagefns.h:142
    """
    assert invert is True or invert is False
    if threstype == "inclusive":
        it = np.logical_and(array >= lowerth, array <= upperth)
    elif threstype == "exclusive":
        it = np.logical_and(array > lowerth, array < upperth)
    array2 = np.logical_xor(invert, it)
    return array2


def regfilt(array, design, comps, mask=None, aggressive=False):
    """
    numpy translation of fsl fsl_regfilt.cc dofilter
    """
    zero_based_comps = [c - 1 for c in comps]

    # setup

    if mask is None:
        mean = array.mean(axis=1)
        mmin = mean.min()
        mmax = mean.max()
        mask = binarise(mean, mmin + 0.01 * (mmax - mmin), mmax)

    mask_vec = np.ravel(mask)
    data = array[mask_vec, :].T
    m, n = data.shape

    mean_r = data.mean(axis=0)
    data -= mean_r[None, :]
    mean_c = design.mean(axis=0)
    design -= mean_c[None, :]

    logging.getLogger("halfpipe").info(f"Data matrix size : {m} x {n}")

    # dofilter

    logging.getLogger("halfpipe").info(f"Calculating maps")

    unmix_matrix = np.linalg.pinv(design)
    maps = unmix_matrix.dot(data)

    noisedes = design[:, zero_based_comps]
    noisemaps = maps[zero_based_comps, :].T

    logging.getLogger("halfpipe").info(f"Calculating filtered data")

    if aggressive:
        new_data = data - noisedes.dot(np.linalg.pinv(noisedes).dot(data))
    else:
        new_data = data - noisedes.dot(noisemaps.T)

    new_data += mean_r[None, :]

    temp_vol = np.zeros_like(array)
    temp_vol[mask_vec, :] = new_data.T

    return temp_vol


class FilterRegressorInputSpec(TransformerInputSpec):
    design_file = traits.File(desc="design file", exists=True, mandatory=True)
    filter_columns = traits.List(traits.Int, mandatory=True)
    mask = traits.File(desc="mask image file name", exists=True)
    aggressive = traits.Bool(default=False, usedefault=True)


class FilterRegressor(Transformer):
    input_spec = FilterRegressorInputSpec

    def _transform(self, array):
        design = readtsv(self.inputs.design_file, dtype=np.float64)

        mask = self.inputs.mask
        if isdefined(mask):
            mask_img = nib.load(mask)
            mask = mask_img.get_fdata(dtype=np.float64)
        else:
            mask = None

        filter_columns = self.inputs.filter_columns

        array2 = regfilt(array, design, filter_columns, mask=mask, aggressive=False)

        return array2
