# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging

import numpy as np
from nipype.interfaces.base import File, isdefined, traits
from numpy import typing as npt

from ..transformer import Transformer, TransformerInputSpec


def binarize(array, lowerth, upperth, threstype="inclusive", invert: bool = False):
    """
    numpy translation of fsl newimage.cc binarise
    default arguments come from newimagefns.h:142
    """

    if threstype == "inclusive":
        it = np.logical_and(array >= lowerth, array <= upperth)
    elif threstype == "exclusive":
        it = np.logical_and(array > lowerth, array < upperth)
    else:
        raise ValueError()

    array2 = np.logical_xor(invert, it)
    return array2


def regfilt(array, design, comps, calculate_mask=True, aggressive=False):
    """
    numpy translation of fsl fsl_regfilt.cc dofilter
    """
    zero_based_comps = [c - 1 for c in comps]

    # setup

    data = array.copy()
    mask_vec: npt.NDArray | None = None
    if calculate_mask is True:
        mean = data.mean(axis=0)
        mmin = mean.min()
        mmax = mean.max()
        mask = binarize(mean, mmin + 0.01 * (mmax - mmin), mmax)
        mask_vec = np.ravel(mask)
        data = data[:, mask_vec]

    m, n = data.shape

    mean_r = data.mean(axis=0)
    data -= mean_r[None, :]
    mean_c = design.mean(axis=0)
    design -= mean_c[None, :]

    logging.getLogger("halfpipe").info(f"Data matrix size : {m} x {n}")

    # dofilter

    logging.getLogger("halfpipe").info("Calculating maps")

    unmix_matrix = np.linalg.pinv(design)
    maps = unmix_matrix @ data

    noisedes = design[:, zero_based_comps]
    noisemaps = maps[zero_based_comps, :].T

    logging.getLogger("halfpipe").info("Calculating filtered data")

    if aggressive:
        new_data = data - noisedes @ (np.linalg.pinv(noisedes) @ data)
    else:
        new_data = data - noisedes @ noisemaps.T

    new_data += mean_r[None, :]

    if calculate_mask is True:
        temp_vol = np.zeros_like(array)
        temp_vol[:, mask_vec] = new_data
    else:
        temp_vol = new_data

    return temp_vol


class FilterRegressorInputSpec(TransformerInputSpec):
    design_file = File(desc="design file", exists=True, mandatory=True)
    filter_columns = traits.List(traits.Int)
    filter_all = traits.Bool(default=False, usedefault=True)
    mask = traits.Either(
        File(desc="mask image file name", exists=True),
        traits.Bool(),
        default=True,
        usedefault=True,
    )
    aggressive = traits.Bool(default=False, usedefault=True)


class FilterRegressor(Transformer):
    input_spec = FilterRegressorInputSpec

    suffix = "regfilt"

    def _transform(self, array):
        design = np.loadtxt(self.inputs.design_file, dtype=np.float64, ndmin=2)

        filter_all = self.inputs.filter_all

        if filter_all is not True:
            filter_columns = self.inputs.filter_columns

        else:
            filter_columns = list(range(1, design.shape[1] + 1))

        calculate_mask = isdefined(self.inputs.mask) and self.inputs.mask is True

        np.nan_to_num(array, copy=False)  # nans create problems further down the line

        array2 = regfilt(
            array,
            design,
            filter_columns,
            calculate_mask=calculate_mask,
            aggressive=self.inputs.aggressive,
        )

        return array2
