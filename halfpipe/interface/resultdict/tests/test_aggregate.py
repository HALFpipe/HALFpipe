# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Sequence

from math import isclose
import numpy as np

from ..aggregate import aggregate_any, aggregate_resultdicts
from ....schema.result import MeanStd, Count


def test_aggregate_any():
    assert aggregate_any("test") == "test"

    assert aggregate_any(["a", "a"]) == "a"

    mean_std_dict = aggregate_any([0.5, 1.0, 1.5])
    assert isinstance(mean_std_dict, dict)

    mean_std = MeanStd.Schema().load(mean_std_dict)
    assert isinstance(mean_std, MeanStd)
    assert isclose(mean_std.mean, 1)

    counts = aggregate_any(["a", "a", "b"])
    assert isinstance(counts, Sequence)
    assert all(Count.Schema().load(c) is not None for c in counts)

    counts = aggregate_any([counts, counts])
    assert isinstance(counts, Sequence)
    assert all(Count.Schema().load(c) is not None for c in counts)


def test_aggregate_any_dict():
    dict_a = {"Mean": 1.0}
    dict_b = {"Mean": 2.0}

    counts = aggregate_any([dict_a, dict_a, dict_b])
    assert isinstance(counts, Sequence)
    for c in counts:
        count = Count.Schema().load(c)
        assert isinstance(count, Count)
        assert isinstance(count.value, dict)

    counts = aggregate_any([counts, counts])
    assert isinstance(counts, Sequence)
    for c in counts:
        count = Count.Schema().load(c)
        assert isinstance(count, Count)
        assert isinstance(count.value, dict)

    counts = aggregate_any([tuple(counts), tuple(counts)])
    assert isinstance(counts, Sequence)
    for c in counts:
        count = Count.Schema().load(c)
        assert isinstance(count, Count)
        assert isinstance(count.value, dict)


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
        tags=dict(sub="c"),
        images=dict(stat="c"),
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

    aggregated, _ = aggregate_resultdicts([result_a, result_b, result_c], across="sub")
    (result,) = aggregated

    subjects = result["tags"]["sub"]
    assert len(subjects) == 3

    fd_perc = result["vals"]["fd_perc"]
    assert isinstance(fd_perc, dict)

    mean_std = MeanStd.Schema().load(fd_perc)
    assert isinstance(mean_std, MeanStd)
    assert isclose(mean_std.mean, 0.2)

    metadata = result["metadata"]

    shape = metadata["acquisition_volume_shape"]
    assert isinstance(shape, list)
    for c in shape:
        count = Count.Schema().load(c)
        assert isinstance(count, Count)
        assert isinstance(count.value, tuple)
        assert len(count.value) == 3

    size = metadata["acquisition_voxel_size"]
    assert isinstance(size, tuple)
    assert len(size) == 3
    assert all(isclose(s, 2.9) for s in size)

    assert all(isclose(a, b) for a, b in zip(slice_timing, metadata["slice_timing"]))
