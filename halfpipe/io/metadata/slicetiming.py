# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import numpy as np


def _get_slice_orders(n_slices):
    sequential = np.arange(n_slices)

    even = np.arange(1, n_slices, 2)
    odd = np.arange(0, n_slices, 2)  # odd/even in one-based

    orders = {
        "sequential increasing": sequential,
        "sequential decreasing": sequential[::-1],
        "alternating increasing even first": [*even, *odd],
        "alternating increasing odd first": [*odd, *even],
        "alternating decreasing even first": [*even, *odd][::-1],
        "alternating decreasing odd first": [*odd, *even][::-1],
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
    order = _get_slice_orders(n_slices)[order_str]

    timings = np.zeros((n_slices,))
    timings[order] = np.arange(n_slices) * slice_duration

    return list(timings)
