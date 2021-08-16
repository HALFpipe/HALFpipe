# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import List, Optional, Union, Sequence

from dataclasses import dataclass, field
from marshmallow_dataclass import class_schema

from .base import BaseSchema
from .filter import ScanFilter


@dataclass
class GlobalSettings:
    pass


@dataclass
class SmoothingSetting:
    fwhm: float


@dataclass
class GrandMeanScalingSetting:
    mean: float


@dataclass
class GaussianTemporalFilterSetting:
    hp_width: float
    lp_width: float


@dataclass
class FrequencyBasedTemporalFilterSetting:
    low: float
    high: float


TemporalFilterSetting = Union[
    GaussianTemporalFilterSetting,
    FrequencyBasedTemporalFilterSetting,
]


@dataclass
class SettingBase:
    ica_aroma: bool = True
    smoothing: Optional[SmoothingSetting] = None
    grand_mean_scaling: Optional[GrandMeanScalingSetting] = None
    bandpass_filter: Optional[TemporalFilterSetting] = None
    confounds_removal: Sequence[str] = field(default_factory=list)


@dataclass
class SettingExtra:
    name: str
    filters: List[ScanFilter]
    output_image: bool


@dataclass
class Setting(SettingBase, SettingExtra):
    pass


SettingBaseSchema = class_schema(SettingBase, base_schema=BaseSchema)
