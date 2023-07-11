# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from functools import reduce
from typing import Iterable

import pandas as pd


def combine_first(data_frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    return reduce(lambda a, b: a.combine_first(b), data_frames)
