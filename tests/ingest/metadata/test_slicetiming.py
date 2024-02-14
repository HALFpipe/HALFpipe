# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose

from halfpipe.ingest.metadata.slicetiming import str_slice_timing


def test_str_slice_timing():
    # based on
    # https://openneuro.org/datasets/ds000117/versions/1.0.4/file-display/task-facerecognition_bold.json

    order_str = "alternating increasing odd first"
    n_slices = 33
    slice_duration = 2.0 / n_slices

    timings = str_slice_timing(order_str, n_slices, slice_duration)

    reference = [
        0,
        1.0325,
        0.06,
        1.095,
        0.12,
        1.155,
        0.1825,
        1.215,
        0.2425,
        1.2775,
        0.3025,
        1.3375,
        0.365,
        1.3975,
        0.425,
        1.46,
        0.485,
        1.52,
        0.5475,
        1.58,
        0.6075,
        1.6425,
        0.6675,
        1.7025,
        0.73,
        1.7625,
        0.79,
        1.825,
        0.85,
        1.885,
        0.9125,
        1.945,
        0.9725,
    ]

    assert all(isclose(a, b, abs_tol=1e-2) for a, b in zip(timings, reference, strict=False))
