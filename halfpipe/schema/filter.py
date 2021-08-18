# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import List, Union
from typing_extensions import Literal

from dataclasses import dataclass


@dataclass
class FilterBase:
    action: Literal["include", "exclude"]


@dataclass
class CutoffFilter(FilterBase):
    field: str
    cutoff: float


@dataclass
class SubgroupFilter(FilterBase):
    variable: str
    levels: List[str]


@dataclass
class MissingFilter(FilterBase):
    variable: str


@dataclass
class TagFilter(FilterBase):
    entity: str
    values: List[str]


ScanFilter = Union[TagFilter, CutoffFilter]
GroupFilter = Union[ScanFilter, SubgroupFilter, MissingFilter]
