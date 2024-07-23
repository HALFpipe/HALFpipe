# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import pandas as pd
import pytest
from halfpipe.design import group_design, prepare_data_frame

tsv_str = """SubjID\tSex\tSite.\tRecur\tAD
11111111\t0\t1\t0\tNA
11111112\t1\t1\t1\tNA
11111113\t0\t1\t2 \tNA
11111114\t1\t1\tNA \tNA
11111115\t0\t1\t1\tNA
"""


@pytest.mark.parametrize(
    "tsv_str",
    [tsv_str, tsv_str.replace("\t", ","), tsv_str.replace("\t", " ")],
)
def test_prepare_data_frame(tmp_path: Path, tsv_str: str):
    spreadsheet_path = tmp_path / "spreadsheet.tsv"

    with open(spreadsheet_path, "w") as file_handle:
        file_handle.write(tsv_str)

    variables: list[dict] = [
        {"name": "SubjID", "type": "id"},
        {"name": "Sex", "type": "categorical", "levels": ["0", "1"]},
        {"name": "Site.", "type": "categorical", "levels": ["1"]},
        {"name": "Recur", "type": "categorical", "levels": ["0", "1", "2"]},
        {"name": "AD", "type": "categorical", "levels": ["0", "1", "2"]},
    ]
    subjects = ["11111111", "11111112", "11111113", "11111114", "11111115"]

    df = prepare_data_frame(spreadsheet_path, variables, subjects)
    assert df.shape == (5, 4)
    assert df["Recur"].dtype == "category"
    assert df["Recur"].notnull().sum() == 4
    assert df["AD"].dtype == "category"


def test_group_design():
    data_frame = pd.DataFrame(
        {
            "subject": ["s1", "s2", "s3", "s4", "s5", "s6"],
            "group": ["A", "A", "B", "B", "C", "C"],
        }
    )
    data_frame = data_frame.set_index("subject")
    data_frame["group"] = data_frame["group"].astype("category")

    subjects = ["s1", "s2", "s3", "s4"]
    contrasts = [
        dict(type="infer", variable=["group"], levels=["A", "B", "C"]),
    ]

    design = group_design(
        data_frame,
        contrasts,
        subjects,
    )
    assert len(design.regressor_list) == 2
