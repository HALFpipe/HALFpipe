# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from types import FunctionType

import numpy as np
import pandas as pd
import pytest

from ...design import prepare_data_frame
from ..base import ResultDict
from ..filter import filter_results, get_categorical_dict, parse_filter_dict


@pytest.mark.parametrize("action", ["include", "exclude"])
def test_filter_group(action: str, tmp_path):
    groups = {"1": "d", "sub-2": "c", "3": "b"}
    data_frame = pd.DataFrame(dict(a=groups))
    data_frame.reset_index(level=0, inplace=True)

    data_frame.to_csv(tmp_path / "spreadsheet.csv", index=False)

    variable_dicts = [
        dict(type="id", name="index"),
        dict(type="categorical", name="a"),
    ]

    data_frame = prepare_data_frame(tmp_path / "spreadsheet.csv", variable_dicts)
    categorical_dict = get_categorical_dict(data_frame, variable_dicts=variable_dicts)

    levels = ["b", "c"]
    filter_dict = dict(
        type="group",
        variable="a",
        levels=levels,
        action=action,
    )

    f = parse_filter_dict(filter_dict, categorical_dict)
    assert isinstance(f, FunctionType)

    for k, v in {**groups, "2": "c", "sub-3": "b"}.items():
        result: ResultDict = {"tags": dict(sub=k)}

        will_keep = f(result)

        expected = v in levels

        if action == "exclude":
            expected = not expected

        assert will_keep == expected


def test_filter_cutoff():
    filter_dict = dict(
        type="cutoff",
        field="a",
        cutoff=1.0,
        action="exclude",
    )

    f = parse_filter_dict(filter_dict)
    assert isinstance(f, FunctionType)

    assert f(dict(tags=dict(), vals=dict(a=0.0))) is True

    assert f(dict(tags=dict(), vals=dict(a=2.0))) is False


def test_filter_missing(tmp_path):
    values = {"1": np.nan, "2": 1.0, "sub-3": np.nan}
    data_frame = pd.DataFrame(dict(a=values))
    data_frame.reset_index(level=0, inplace=True)

    spreadsheet = tmp_path / "spreadsheet.csv"
    data_frame.to_csv(spreadsheet, index=False)

    variable_dicts = [
        dict(type="id", name="index"),
        dict(type="continuous", name="a"),
    ]

    filter_dict = dict(
        type="missing",
        variable="a",
        action="exclude",
    )

    for k, v in {**values, "sub-1": np.nan, "3": np.nan}.items():
        result: ResultDict = {"tags": dict(sub=k)}
        results = filter_results(
            [result],
            filter_dicts=[filter_dict],
            spreadsheet=spreadsheet,
            variable_dicts=variable_dicts,
        )
        assert len(results) == int(np.isfinite(v))
