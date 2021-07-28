# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Tuple

from fmriprep.config import DEFAULT_MEMORY_MIN_GB

from ..io.metadata.niftiheader import NiftiheaderLoader


def calc_bold_gb(shape: Tuple[int, int, int, int]) -> Tuple[float, float]:
    x, y, z, t = shape
    volume_gb: float = x * y * z * 8 / 2 ** 30
    series_gb: float = volume_gb * t

    return volume_gb, series_gb


class MemoryCalculator:
    def __init__(self, database=None, bold_file=None, bold_shape=[72, 72, 72], bold_tlen=200):

        if database is not None:
            bold_file = next(iter(
                database.get(datatype="func", suffix="bold")
            ))

        if bold_file is not None:
            header, _ = NiftiheaderLoader.load(bold_file)
            if header is not None:
                bold_shape = header.get_data_shape()

        x, y, z = bold_shape[:3]

        t = 1
        for n in bold_shape[3:]:
            t *= n

        if t == 1:
            t = bold_tlen

        self.volume_gb, self.series_gb = calc_bold_gb((x, y, z, t))
        self.volume_std_gb, self.series_std_gb = calc_bold_gb((97, 115, 97, t))

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
