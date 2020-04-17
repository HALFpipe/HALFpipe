# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
import nibabel as nb

from fmriprep.config import DEFAULT_MEMORY_MIN_GB

from ..utils import first


class MemoryCalculator:
    def __init__(self, bold_file=None, bold_shape=[72, 72, 72], bold_tlen=200):
        if bold_file:
            bold_shape = nb.load(bold_file).shape
        self.volume_gb = np.product(bold_shape[:3]) * 8 / 2 ** 30
        bold_tlen = 1
        if len(bold_shape) > 3:
            bold_tlen = bold_shape[3]
        self.series_gb = self.volume_gb * bold_tlen

        std_bold_shape = [91, 109, 91, bold_tlen]  # template size

        self.volume_std_gb = np.product(std_bold_shape[:-1]) * 8 / 2 ** 30
        self.series_std_gb = self.volume_std_gb * bold_tlen

        self.min_gb = DEFAULT_MEMORY_MIN_GB

    def __hash__(self):
        return hash(
            (
                self.volume_gb,
                self.series_gb,
                self.volume_std_gb,
                self.series_std_gb,
                self.min_gb,
            )
        )


def memcalc_from_database(database):
    return MemoryCalculator(
        bold_file=first(database.get(datatype="func", suffix="bold"))
    )
