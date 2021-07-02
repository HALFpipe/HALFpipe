# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from typing import Dict, Set, Type, List

from .base import ModelAlgorithm
from .descriptive import Descriptive
from .flame1 import FLAME1
from .heterogeneity import Heterogeneity
from .mcar import MCARTest

algorithms: Dict[str, Type[ModelAlgorithm]] = dict(
    descriptive=Descriptive,
    flame1=FLAME1,
    heterogeneity=Heterogeneity,
    mcartest=MCARTest,
)


def make_algorithms_set(algorithms_to_run: List[str]) -> Set[str]:
    # update algorithms
    # remove duplicates and always run descriptive

    algorithm_set = set(algorithms_to_run) | frozenset(["descriptive"])

    return algorithm_set
