# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose
from typing import Mapping

import numpy as np

from ..aggregate import aggregate, summarize
from ..base import Categorical, Continuous


def test_summarize():
    assert summarize(["test"]) == "test"

    assert summarize(["a", "a"]) == "a"

    s = summarize([0.5, 1.0, 1.5])
    assert isinstance(s, str)

    c = Continuous.load(s)
    assert isinstance(c, Continuous)
    assert isclose(c.mean, 1)

    s = summarize(["a", "a", "b"])
    assert isinstance(s, list)
    assert len(s) == 2

    d = Categorical.load(s)
    assert isinstance(d, Categorical)

    s = summarize([d, d])
    assert isinstance(s, list)
    assert len(s) == 2


def test_summarize_dict():
    dict_a = {"Mean": 1.0}
    dict_b = {"Mean": 2.0}

    s = summarize([dict_a, dict_a, dict_b])
    assert isinstance(s, list)

    c = Categorical.load(s)
    assert isinstance(c, Categorical)
    assert isinstance(c.counter, Mapping)

    s = summarize([c, c])
    assert isinstance(s, list)

    c = Categorical.load(s)
    assert isinstance(c, Categorical)
    assert isinstance(c.counter, Mapping)

    s = summarize([(c,), (c,)])
    assert isinstance(s, list)

    c = Categorical.load(s)
    assert isinstance(c, Categorical)
    assert isinstance(c.counter, Mapping)


def test_aggregate_resultdicts():
    slice_timing = list(np.linspace(0, 2, 33))

    result_a = dict(
        tags=dict(sub="a"),
        images=dict(stat="a"),
        vals=dict(
            dummy_scans=1,
            mean_fd=0.1,
            fd_perc=dict(mean=0.2, std=0.2, n_observations=1, n_missing=0),
        ),
        metadata=dict(
            slice_timing=slice_timing,
            acquisition_volume_shape=(64, 64, 32),
            acquisition_voxel_size=(2.9, 2.9, 2.9),
            setting=dict(
                ica_aroma=False,
            ),
        ),
    )
    result_b = dict(
        tags=dict(sub="b"),
        images=dict(stat="b"),
        vals=dict(
            dummy_scans=2,
            mean_fd=0.2,
            fd_perc=dict(mean=0.1, std=0.2, n_observations=1, n_missing=0),
        ),
        metadata=dict(
            slice_timing=slice_timing,
            acquisition_volume_shape=(64, 64, 31),
            acquisition_voxel_size=(2.9, 2.9, 2.9),
            setting=dict(
                ica_aroma=False,
            ),
        ),
    )
    result_c = dict(
        tags=dict(sub=["c"]),
        images=dict(stat=["c"]),
        vals=dict(
            dummy_scans=2,
            mean_fd=0.2,
            fd_perc=0.3,
        ),
        metadata=dict(
            slice_timing=slice_timing,
            acquisition_volume_shape=(64, 64, 31),
            acquisition_voxel_size=(2.9, 2.9, 2.9),
            setting=dict(
                ica_aroma=False,
            ),
        ),
    )

    aggregated, _ = aggregate([result_a, result_b, result_c], across_key="sub")
    (result,) = aggregated

    subjects = result["tags"]["sub"]
    assert len(subjects) == 3

    stat = result["images"]["stat"]
    assert isinstance(stat, list)
    assert len(stat) == 3

    fd_perc = result["vals"]["fd_perc"]
    assert isinstance(fd_perc, str)

    c = Continuous.load(fd_perc)
    assert isinstance(c, Continuous)
    assert isclose(c.mean, 0.2)

    metadata = result["metadata"]

    shape = metadata["acquisition_volume_shape"]
    assert isinstance(shape, list)
    assert len(shape) == 2

    d = Categorical.load(shape)
    assert isinstance(d, Categorical)
    assert isinstance(d.counter, Mapping)
    assert len(d.counter) == 2

    size = metadata["acquisition_voxel_size"]
    assert isinstance(size, tuple)
    assert len(size) == 3
    assert all(isclose(s, 2.9) for s in size)

    assert all(isclose(a, b) for a, b in zip(slice_timing, metadata["slice_timing"]))


def test_aggregate_resultdicts_heterogenous():
    result_a = dict(
        tags=dict(sub="a", task="x", model="aggregateAcrossRuns"),
        images=dict(stat="a"),
        vals=dict(
            dummy_scans=1,
        ),
        metadata=dict(
            setting=dict(
                ica_aroma=False,
            ),
        ),
    )
    result_b = dict(
        tags=dict(sub="b", task="x", model="aggregateAcrossRuns"),
        images=dict(stat="b"),
        vals=dict(
            dummy_scans=1,
        ),
        metadata=dict(
            setting=dict(
                ica_aroma=False,
            ),
        ),
    )
    result_c = dict(
        tags=dict(sub="c", task="x", run=["02"]),
        images=dict(stat="c"),
        vals=dict(
            dummy_scans=1,
        ),
        metadata=dict(
            setting=dict(
                ica_aroma=False,
            ),
        ),
    )

    aggregated, _ = aggregate([result_a, result_b, result_c], across_key="sub")
    (result,) = aggregated

    subjects = result["tags"]["sub"]
    assert len(subjects) == 3
