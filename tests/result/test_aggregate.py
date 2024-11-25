# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose
from typing import Mapping

import numpy as np
import pytest

from halfpipe.result.aggregate import aggregate_results, summarize, summarize_metadata
from halfpipe.result.base import ResultDict
from halfpipe.result.variables import Categorical, Continuous


def test_summarize() -> None:
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


def test_summarize_dict() -> None:
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


def test_aggregate_resultdicts() -> None:
    slice_timing = list(np.linspace(0, 2, 33))

    result_a: ResultDict = {
        "tags": dict(sub="a"),
        "images": dict(stat="a"),
        "vals": dict(
            dummy_scans=1,
            mean_fd=0.1,
            fd_perc=dict(mean=0.2, std=0.2, n_observations=1, n_missing=0),
        ),
        "metadata": dict(
            slice_timing=slice_timing,
            acquisition_volume_shape=(64, 64, 32),
            acquisition_voxel_size=(2.9, 2.9, 2.9),
            setting=dict(
                ica_aroma=False,
            ),
        ),
    }
    result_b: ResultDict = {
        "tags": dict(sub="b"),
        "images": dict(stat="b"),
        "vals": dict(
            dummy_scans=2,
            mean_fd=0.2,
            fd_perc=dict(mean=0.1, std=0.2, n_observations=1, n_missing=0),
        ),
        "metadata": dict(
            slice_timing=slice_timing,
            acquisition_volume_shape=(64, 64, 31),
            acquisition_voxel_size=(2.9, 2.9, 2.9),
            setting=dict(
                ica_aroma=False,
            ),
        ),
    }
    result_c: ResultDict = {
        "tags": dict(sub=["c"]),
        "images": dict(stat=["c"]),
        "vals": dict(
            dummy_scans=2,
            mean_fd=0.2,
            fd_perc=0.3,
        ),
        "metadata": dict(
            slice_timing=slice_timing,
            acquisition_volume_shape=(64, 64, 31),
            acquisition_voxel_size=(2.9, 2.9, 2.9),
            setting=dict(
                ica_aroma=False,
            ),
        ),
    }

    aggregated, _ = aggregate_results([result_a, result_b, result_c], across_key="sub")
    (result,) = aggregated
    result = summarize_metadata(result)

    subjects = result["tags"]["sub"]
    assert subjects == ["a", "b", "c"]

    stat = result["images"]["stat"]
    assert stat == ["a", "b", "c"]

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

    for i, a in enumerate(slice_timing):
        assert isclose(a, metadata["slice_timing"][i])


def test_aggregate_resultdicts_heterogenous() -> None:
    result_a: ResultDict = {
        "tags": dict(sub="a", task="x", model="aggregateAcrossRuns"),
        "images": dict(stat="a"),
        "vals": dict(dummy_scans=1),
        "metadata": dict(
            setting=dict(
                ica_aroma=False,
            ),
        ),
    }
    result_b: ResultDict = {
        "tags": dict(sub="b", task="x", model="aggregateAcrossRuns"),
        "images": dict(stat="b"),
        "vals": dict(dummy_scans=1),
        "metadata": dict(
            setting=dict(
                ica_aroma=False,
            ),
        ),
    }
    result_c: ResultDict = {
        "tags": dict(sub="c", task="x", run=["02"]),
        "images": dict(stat="c"),
        "vals": dict(
            dummy_scans=1,
        ),
        "metadata": dict(
            setting=dict(
                ica_aroma=False,
            ),
        ),
    }

    aggregated, _ = aggregate_results([result_a, result_b, result_c], across_key="sub")
    (result,) = aggregated

    subjects = result["tags"]["sub"]
    assert len(subjects) == 3


def test_aggregate_resultdicts_missing_tag() -> None:
    results: list[ResultDict] = list()
    for sub in ["a", "b", "c"]:
        for run in ["01", "02"]:
            results.append(
                {
                    "tags": dict(sub=sub, run=run),
                    "images": dict(stat=sub),
                    "vals": dict(),
                    "metadata": dict(),
                }
            )
    results.append(
        {
            "tags": dict(sub="d", run="01"),
            "images": dict(stat="d"),
            "vals": dict(),
            "metadata": dict(),
        }
    )
    results.append(
        {
            "tags": dict(sub="x"),
            "images": dict(stat="x"),
            "vals": dict(),
            "metadata": dict(),
        }
    )

    aggregated_results, other_results = aggregate_results(results, across_key="run")
    sub_a, sub_b, sub_c = aggregated_results
    assert sub_a["tags"] == {"run": ["01", "02"], "sub": "a"}
    assert sub_b["tags"] == {"run": ["01", "02"], "sub": "b"}
    assert sub_c["tags"] == {"run": ["01", "02"], "sub": "c"}
    assert len(other_results) == 2

    aggregated_results, other_results = aggregate_results([*aggregated_results, *other_results], across_key="sub")
    (result,) = aggregated_results
    assert result["tags"] == {"sub": ["a", "b", "c", "d", "x"]}
    assert len(other_results) == 0


@pytest.mark.timeout(4)
def test_aggregate_many() -> None:
    results: list[ResultDict] = list()

    n = 32

    for i in range(1, n + 1):
        results.append(
            {
                "tags": dict(sub=f"{i:02d}", task="x", run="01"),
                "images": dict(stat=f"sub-{i:02d}_x.nii.gz"),
                "vals": dict(dummy_scans=1),
                "metadata": dict(),
            }
        )

    for i in range(1, n + 1):
        for j in range(1, 4):
            tags: dict[str, str | list[str]] = dict(sub=f"{i:02d}", task="y", run=f"{j:02d}")

            if j == 1:  # make heterogeneous
                tags["model"] = "aggregateAcrossDirs"
            if j in [2, 3]:
                tags["acq"] = "extra"
            if j == 3:
                tags["something"] = "else"

            results.append(
                {
                    "tags": tags,
                    "images": dict(stat=f"sub-{i:02d}_run-{j:02d}_y.nii.gz"),
                    "vals": dict(dummy_scans=1),
                    "metadata": dict(),
                }
            )

    aggregated, non_aggregated = aggregate_results(results, across_key="run")
    assert len(aggregated) == n
    assert len(non_aggregated) == n
