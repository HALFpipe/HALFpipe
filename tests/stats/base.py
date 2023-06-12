# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import NamedTuple


class Dataset(NamedTuple):
    subjects: list[str]
    cope_files: list[Path]
    var_cope_files: list[Path]
    mask_files: list[Path]
    regressors: dict[str, list[float]]
    contrasts: list[tuple]
