# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from nipype.interfaces.base import traits
from numpy import typing as npt

from ..transformer import Transformer, TransformerInputSpec


def bandpass_temporal_filter(array, hp_sigma, lp_sigma):
    """
    numpy translation of fsl newimagefuns.h bandpass_temporal_filter
    """

    if hp_sigma <= 0:
        hp_mask_size_minus = 0
    else:
        hp_mask_size_minus = int(np.floor(hp_sigma * 3))

    hp_mask_size_plus = hp_mask_size_minus

    if lp_sigma <= 0:
        lp_mask_size_minus = 0
    else:
        lp_mask_size_minus = int(np.floor(lp_sigma * 20)) + 2

    lp_mask_size_plus = lp_mask_size_minus

    hp_exp = np.zeros(0)
    if hp_sigma > 0:
        hp_exp = np.zeros(hp_mask_size_minus + hp_mask_size_plus + 1)
        for t in range(-hp_mask_size_minus, hp_mask_size_plus + 1):
            hp_exp[t] = np.exp(-0.5 * (float(t * t)) / (hp_sigma * hp_sigma))

    lp_exp = np.zeros(0)
    if lp_sigma > 0:
        total = 0.0
        lp_exp = np.zeros(lp_mask_size_minus + lp_mask_size_plus + 1)
        for t in range(-lp_mask_size_minus, lp_mask_size_plus + 1):
            lp_exp[t] = np.exp(-0.5 * (float(t * t)) / (lp_sigma * lp_sigma))
            total += lp_exp[t]
        for t in range(-lp_mask_size_minus, lp_mask_size_plus + 1):
            lp_exp[t] /= total

    m, sourcetsize = array.shape
    array2 = np.zeros_like(array)

    if hp_sigma > 0:
        c0 = None
        for t in range(sourcetsize):
            a: float = 0.0
            b: npt.NDArray = np.zeros((m,), dtype=array.dtype)
            c: float | npt.NDArray = 0.0
            d: npt.NDArray = np.zeros((m,), dtype=array.dtype)
            n: float = 0.0

            for tt in range(
                max(t - hp_mask_size_minus, 0),
                min(t + hp_mask_size_plus, sourcetsize - 1) + 1,
            ):
                dt = tt - t
                w = hp_exp[dt]
                a += w * dt
                b += w * array[:, tt]
                c += w * dt * dt
                d += w * dt * array[:, tt]
                n += w

            tmpdenom = c * n - a * a
            if not np.isclose(tmpdenom, 0):
                c = (b * c - a * d) / tmpdenom
                if c0 is None:
                    c0 = c
                array2[:, t] = c0 + array[:, t] - c
            else:
                array2[:, t] = array[:, t]

        array2 -= array2.mean(axis=1)[:, None]

        np.copyto(array, array2)  # destination, then source

    if lp_sigma > 0:
        for t in range(sourcetsize):
            lp_total = np.zeros((m,), dtype=array.dtype)
            sum = 0

            for tt in range(
                max(t - lp_mask_size_minus, 0),
                min(t + lp_mask_size_plus, sourcetsize - 1) + 1,
            ):
                lp_total += array[:, tt] * lp_exp[tt - t]
                sum += lp_exp[tt - t]

            if sum > 0:
                array2[:, t] = lp_total / sum
            else:
                array2[:, t] = lp_total

        np.copyto(array, array2)

    return array


class TemporalFilterInputSpec(TransformerInputSpec):
    lowpass_sigma = traits.Float(default=-1, usedefault=True)
    highpass_sigma = traits.Float(default=-1, usedefault=True)


class TemporalFilter(Transformer):
    input_spec = TemporalFilterInputSpec

    suffix = "bptf"

    def _transform(self, array):
        lowpass_sigma = self.inputs.lowpass_sigma
        highpass_sigma = self.inputs.highpass_sigma

        np.nan_to_num(array, copy=False)  # nans create problems further down the line

        array = array.T  # need to transpose

        array2 = bandpass_temporal_filter(array, highpass_sigma, lowpass_sigma)

        array2 = array2.T  # restore

        return array2
