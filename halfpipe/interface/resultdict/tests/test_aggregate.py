# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Sequence

from math import isclose

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
    result_a = dict(
        tags=dict(sub="a"),
        images=dict(stat="a"),
        vals=dict(
            dummy_scans=1,
            mean_fd=0.1,
        ),
        metadata=dict(
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
        ),
        metadata=dict(
            acquisition_volume_shape=(64, 64, 31),
            acquisition_voxel_size=(2.9, 2.9, 2.9),
            setting=dict(
                ica_aroma=False,
            ),
        ),
    )
    aggregated, _ = aggregate_resultdicts([result_a, result_b], across="sub")
    (result,) = aggregated
    assert len(result["tags"]["sub"]) == 2
