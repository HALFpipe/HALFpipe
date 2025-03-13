# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
import scipy.stats
from nipype.interfaces.base import File, isdefined, traits
from numpy import typing as npt

from ...logging import logger
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


def regfilt(
    array: npt.NDArray[np.float64],
    design: npt.NDArray[np.float64],
    comps: list[int],
    calculate_mask: bool = True,
    aggressive: bool = False,
) -> npt.NDArray:
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
    logger.info(f"Data matrix size : {m} x {n}")

    mean_r = data.mean(axis=0)
    data -= mean_r[None, :]
    # standardize design for numerical stability
    design = scipy.stats.zscore(design, axis=0)

    # dofilter
    noisedes = design[:, zero_based_comps]

    if aggressive:
        logger.info("Calculating maps")
        maps, _, _, _ = np.linalg.lstsq(noisedes, data, rcond=None)
        logger.info("Calculating filtered data")
        new_data = data - noisedes @ maps
    else:
        logger.info("Calculating maps")
        maps, _, _, _ = np.linalg.lstsq(design, data, rcond=None)
        noisemaps = maps[zero_based_comps, :]
        logger.info("Calculating filtered data")
        new_data = data - noisedes @ noisemaps

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
    filter_all = traits.Bool(default_value=False, usedefault=True)
    mask = traits.Either(
        File(desc="mask image file name", exists=True),
        traits.Bool(),
        default=True,
        usedefault=True,
    )
    aggressive = traits.Bool(default_value=False, usedefault=True)


class FilterRegressor(Transformer):
    input_spec = FilterRegressorInputSpec

    suffix = "regfilt"

    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        design = np.loadtxt(self.inputs.design_file, dtype=np.float64, ndmin=2)

        filter_all = self.inputs.filter_all
        if filter_all is True:
            filter_columns = list(range(1, design.shape[1] + 1))
        else:
            filter_columns = self.inputs.filter_columns

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
