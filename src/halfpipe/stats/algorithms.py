# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Type

from .base import ModelAlgorithm
from .descriptive import Descriptive
from .flame1 import FLAME1
from .heterogeneity import Heterogeneity
from .mcar import MCARTest

# according to https://github.com/poldracklab/fitlins/blob/0.6.2/fitlins/workflows/base.py
modelfit_aliases = dict(
    copes="effect",
    var_copes="variance",
    zstats="z",
    tstats="t",
    fstats="f",
    masks="mask",
)

algorithms: dict[str, Type[ModelAlgorithm]] = dict(
    descriptive=Descriptive,
    flame1=FLAME1,
    heterogeneity=Heterogeneity,
    mcartest=MCARTest,
)


def make_algorithms_dict(
    algorithms_to_run: list[str],
) -> dict[str, Type[ModelAlgorithm]]:
    # update algorithms
    # remove duplicates and always run descriptive

    algorithm_set = set(algorithms_to_run) | frozenset(["descriptive"])

    algorithms_dict = {name: algorithms[name] for name in algorithm_set}
    return algorithms_dict
