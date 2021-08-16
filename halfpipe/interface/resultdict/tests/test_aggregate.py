# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose

from ..aggregate import aggregate_if_possible, aggregate_resultdicts
from ....schema.result import MeanStd, Count


def test_aggregate_if_possible():
    assert aggregate_if_possible("test") == "test"

    assert aggregate_if_possible(["a", "a"]) == "a"

    mean_std = aggregate_if_possible([0.5, 1.0, 1.5])
    assert isinstance(mean_std, MeanStd)
    assert isclose(mean_std.mean, 1)

    count_list = aggregate_if_possible(["a", "a", "b"])
    assert isinstance(count_list, list)
    assert all(isinstance(c, Count) for c in count_list)

    count_list = aggregate_if_possible([count_list, count_list])
    assert isinstance(count_list, list)
    assert all(isinstance(c, Count) for c in count_list)


def test_aggregate_if_possible_dict():
    dict_a = {"Mean": 1.0}
    dict_b = {"Mean": 2.0}

    count_list = aggregate_if_possible([dict_a, dict_a, dict_b])
    assert isinstance(count_list, list)
    assert all(
        isinstance(c, Count) and isinstance(c.value, dict) for c in count_list
    )

    count_list = aggregate_if_possible([count_list, count_list])
    assert isinstance(count_list, list)
    assert all(
        isinstance(c, Count) and isinstance(c.value, dict) for c in count_list
    )

    count_list = aggregate_if_possible([tuple(count_list), tuple(count_list)])
    assert isinstance(count_list, list)
    assert all(
        isinstance(c, Count) and isinstance(c.value, dict) for c in count_list
    )


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

    from pprint import pprint
    pprint(result)
