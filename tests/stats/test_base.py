# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from halfpipe.stats.base import listwise_deletion


def test_listwise_deletion():
    missing_proportion = 0.05

    arrays = []
    for i in [1, 2, 3, 4]:
        x = np.random.randn(100, i)
        x[np.random.rand(*x.shape) < missing_proportion] = np.nan
        arrays.append(x)

    assert all(np.all(np.isfinite(a)) for a in listwise_deletion(*arrays))

    assert 1 == len(set(a.shape[0] for a in listwise_deletion(*arrays)))
