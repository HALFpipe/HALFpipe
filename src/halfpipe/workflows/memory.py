# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import NamedTuple, Tuple, Union

import pint
from templateflow.api import get as get_template

from ..ingest.metadata.niftiheader import NiftiheaderLoader
from .configurables import configurables
from .constants import Constants

ureg = pint.UnitRegistry()


class MemoryCalculator(NamedTuple):
    volume_gb: float
    series_gb: float

    volume_std_gb: float
    series_std_gb: float

    min_gb: float = 1.0  # we reserve a gigabyte for each command

    @classmethod
    def from_bold_shape(cls, x: int = 72, y: int = 72, z: int = 72, t: int = 200):
        volume_gb, series_gb = cls.calc_bold_gb((x, y, z, t))

        reference_file = get_template(
            configurables.reference_space,
            resolution=configurables.reference_res,
            desc="brain",
            suffix="mask",
        )
        assert isinstance(reference_file, Path)
        header, _ = NiftiheaderLoader.load(str(reference_file))
        assert header is not None
        reference_shape = header.get_data_shape()

        x, y, z = reference_shape[:3]
        volume_std_gb, series_std_gb = cls.calc_bold_gb((x, y, z, t))

        return MemoryCalculator(
            volume_gb=volume_gb,
            series_gb=series_gb,
            volume_std_gb=volume_std_gb,
            series_std_gb=series_std_gb,
        )

    @classmethod
    def default(cls):
        return MemoryCalculator.from_bold_shape()

    @classmethod
    def from_bold_file(cls, bold_file: Union[str, Path]):
        header, _ = NiftiheaderLoader.load(str(bold_file))
        if header is not None:
            bold_shape = header.get_data_shape()

            t = 1
            for n in bold_shape[3:]:
                t *= n

            x, y, z = bold_shape[:3]

            if t == 1:
                return cls.from_bold_shape(x=x, y=y, z=z)

            return cls.from_bold_shape(x=x, y=y, z=z, t=t)

        return cls.default()

    @classmethod
    def calc_bold_gb(cls, shape: Tuple[int, int, int, int]) -> Tuple[float, float]:
        x, y, z, t = shape
        volume_bytes = x * y * z * 8 * ureg.bytes

        volume_gb: float = volume_bytes.to(ureg.gigabytes).m
        series_gb: float = volume_gb * t

        min_gb: float = cls._field_defaults["min_gb"]

        volume_gb = max(min_gb, volume_gb)
        series_gb = max(min_gb, series_gb)

        return round(volume_gb, 3), round(series_gb, 3)
