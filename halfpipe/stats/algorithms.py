# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from typing import Dict, Type

from .base import ModelAlgorithm
from .flame1 import FLAME1
from .heterogeneity import Heterogeneity
from .mcar import MCARTest

algorithms: Dict[str, Type[ModelAlgorithm]] = dict(
    flame1=FLAME1,
    heterogeneity=Heterogeneity,
    mcartest=MCARTest,
)
