# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any, Mapping, Sequence, Union, List, Type, ClassVar

from dataclasses import dataclass, field
from marshmallow import Schema
from marshmallow_dataclass import add_schema

import numpy as np

from .base import BaseSchema
from .setting import SettingBase


@add_schema(base_schema=BaseSchema)
@dataclass
class MeanStd:
    mean: float
    std: float
    n_observations: int
    n_missing: int

    Schema: ClassVar[Type[Schema]] = Schema

    @classmethod
    def from_array(cls, array: List[float]) -> "MeanStd":
        value_array = np.array(array, dtype=float)

        mean = float(np.nanmean(value_array))
        std = float(np.nanstd(value_array))
        n_observations = int(value_array.size)
        n_missing = int(np.sum(np.isnan(value_array)))

        return cls(
            mean=mean, std=std, n_observations=n_observations, n_missing=n_missing
        )


@add_schema(base_schema=BaseSchema)
@dataclass
class Count:
    value: Any
    count: int

    Schema: ClassVar[Type[Schema]] = Schema


@add_schema(base_schema=BaseSchema)
@dataclass
class Result:
    tags: Mapping[str, Union[str, List[str]]] = field(default_factory=dict)

    images: Mapping[str, str] = field(default_factory=dict)
    reports: Mapping[str, str] = field(default_factory=dict)

    vals: Mapping[str, Union[
        str,
        float,
        Sequence[int],
        Sequence[float],
        List[Count],
        MeanStd,
    ]] = field(default_factory=dict)

    metadata: Mapping[str, Union[
        str,
        float,
        Sequence[int],
        Sequence[float],
        List[Count],
        MeanStd,
        SettingBase,
    ]] = field(default_factory=dict)

    Schema: ClassVar[Type[Schema]] = Schema
