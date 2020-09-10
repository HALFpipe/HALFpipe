# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import numpy as np

from itertools import zip_longest

from ...utils import removenone, ravel


def _get_slice_orders(n_slices):
    a = n_slices // 2
    b = n_slices - a

    sequential = np.arange(n_slices)
    interleave_even = removenone(ravel(zip_longest(sequential[:b], sequential[b:])))
    interleave_odd = removenone(ravel(zip_longest(sequential[b:], sequential[:b])))

    orders = {
        "sequential increasing": sequential,
        "sequential decreasing": sequential[::-1],
        "alternating increasing even first": interleave_even,
        "alternating increasing odd first": interleave_odd,
        "alternating decreasing even first": interleave_even[::-1],
        "alternating decreasing odd first": interleave_odd[::-1],
    }

    return orders


def slice_timing_str(slice_times):
    slice_times = np.array(slice_times)

    values, inverse, counts = np.unique(slice_times, return_inverse=True, return_counts=True)

    counts = set(counts)
    if len(counts) != 1:
        return "unknown"

    (multiband_factor,) = counts

    order = inverse[: len(values)]

    orders = _get_slice_orders(len(order))

    for name, indices in orders.items():
        if np.allclose(order, indices):
            if multiband_factor > 1:
                return f" {name} with multi-band acceleration factor {multiband_factor}"
            else:
                return name

    return "unknown"


def str_slice_timing(order_str, n_slices, slice_duration):
    orders = _get_slice_orders(n_slices)

    return list(np.array(orders[order_str], dtype=np.float64) * slice_duration)
