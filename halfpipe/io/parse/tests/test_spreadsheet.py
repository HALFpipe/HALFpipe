# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import List, Union

from pathlib import Path
from random import choice, random
from string import ascii_letters, digits
from collections import OrderedDict
from math import isclose

import pytest
import numpy as np
import pandas as pd

from ..spreadsheet import loadspreadsheet

vest_str = """/NumWaves       2
/NumPoints      9
/PPheights              1.287529e+00    1.288630e+00

/Matrix
9.296896e-02    5.568093e-02
8.750945e-02    4.476671e-02
8.189379e-02    3.381361e-02
7.606981e-02    2.284223e-02
7.002674e-02    1.186821e-02
6.377261e-02    8.882643e-04
5.732179e-02    -1.023927e-02
5.068793e-02    -2.160801e-02
4.388237e-02    -3.310538e-02

"""

@pytest.mark.parametrize("extension,delimiter", [
    (".tsv", "\t"),
    (".csv", ","),
    (".csv", ";"),
    (".txt", " "),
    (".txt", "  "),
    (".txt", "\t"),
    (".txt", ","),
    (".txt", ";"),
    ("", " "),
    ("", "  "),
    ("", "\t"),
    ("", ","),
    ("", ";"),
])
@pytest.mark.parametrize("header,index,n_str_columns,n_float_columns", [
    (True, True, 10, 0),
    (True, True, 10, 10),
    (True, False, 10, 0),
    (True, False, 10, 10),
    (False, False, 10, 10),
])
def test_loadspreadsheet_dtypes(
    tmp_path: Path,
    extension: str,
    delimiter: str,
    header: bool,
    n_str_columns: int,
    n_float_columns: int,
    index: bool,
):
    file_name = tmp_path / f"data{extension}"

    def random_str(length: int = 30):
        return "".join(
            choice([*ascii_letters, *digits]) for n in range(length)
        )

    n_rows = 10

    records: OrderedDict[str, List[Union[str, float]]] = OrderedDict([
        (f"x{i}", [random_str(5) for _ in range(n_rows)])
        for i in range(n_str_columns)
    ])

    records.update(OrderedDict([
        (f"y{i}", [random() for _ in range(n_rows)])
        for i in range(n_float_columns)
    ]))

    data_frame = pd.DataFrame.from_records(records)
    data_frame.index = [f"row{i:d}" for i in range(1, n_rows + 1)]

    data_frame_str = data_frame.to_csv(sep="\1", header=header, index=index)
    data_frame_str = data_frame_str.replace("\1", delimiter)

    with open(file_name, "w") as file_pointer:
        file_pointer.write(data_frame_str)

    spreadsheet = loadspreadsheet(file_name)

    if header:
        assert all(
            a == b
            for a, b in zip(data_frame.columns, spreadsheet.columns)
        )

    assert all(
        isclose(a, b) if isinstance(a, float) else a == b
        for a, b in zip(data_frame.values.ravel(), spreadsheet.values.ravel())
    )


@pytest.fixture(scope="module", params=[
    (1, 1),
    (10, 1),
    (1, 10),
    (10, 10),
])
def data_frame(request):
    return pd.DataFrame(
        np.random.randn(*request.param),
        index=[f"row{i:d}" for i in range(1, request.param[0] + 1)],
        columns=[f"column{i:d}" for i in range(1, request.param[1] + 1)],
    )


@pytest.mark.parametrize("extension,delimiter", [
    (".tsv", "\t"),
    (".csv", ","),
    (".csv", ";"),
    (".txt", " "),
    (".txt", "  "),
    (".txt", "\t"),
    (".txt", ","),
    (".txt", ";"),
    ("", " "),
    ("", "  "),
    ("", "\t"),
    ("", ","),
    ("", ";"),
])
@pytest.mark.parametrize("header,index,blank_lines_before_header,blank_lines_after_header", [
    (False, False, 0, 0),
    (False, False, 0, 1),
    (True, False, 0, 0),
    (True, True, 1, 1),
])
@pytest.mark.parametrize("comment_prefix,n_comment_lines", [
    ("", 0),
    ("#", 1),
    ("#", 2),
    ("%", 2),
    ("/", 2),
    ("//", 2),
])
@pytest.mark.parametrize("n_trailing_spaces", [0, 2])
def test_loadspreadsheet_delimited(
    tmp_path: Path,
    data_frame: pd.DataFrame,
    index: bool,
    extension: str,
    delimiter: str,
    header: bool,
    blank_lines_before_header: int,
    blank_lines_after_header: int,
    comment_prefix: str,
    n_comment_lines: int,
    n_trailing_spaces: int,
):
    file_name = tmp_path / f"data{extension}"

    comment_str = "\n".join(
        f"{comment_prefix}comment{i}"
        for i in range(1, n_comment_lines + 1)
    )
    if len(comment_str) > 0:
        comment_str += "\n"

    data_frame_str = data_frame.to_csv(sep="\1", header=True, index=index)
    data_frame_str = data_frame_str.replace("\1", delimiter)
    data_frame_lines = data_frame_str.splitlines()

    header_str = data_frame_lines[0]
    data_lines = data_frame_lines[1:]

    trailing_spaces_str = " " * n_trailing_spaces

    with open(file_name, "w") as file_pointer:
        file_pointer.write(comment_str)

        for _ in range(blank_lines_before_header):
            file_pointer.write("\n")

        if header:
            file_pointer.write(header_str)
            file_pointer.write(trailing_spaces_str)
            file_pointer.write("\n")

        for _ in range(blank_lines_after_header):
            file_pointer.write("\n")

        for data_line in data_lines:
            file_pointer.write(data_line)
            file_pointer.write(trailing_spaces_str)
            file_pointer.write("\n")

    spreadsheet = loadspreadsheet(file_name)

    if header:
        assert all(
            a == b
            for a, b in zip(data_frame.columns, spreadsheet.columns)
        )

    assert np.allclose(data_frame.values, spreadsheet.values)


@pytest.mark.parametrize("header", [True, False])
@pytest.mark.parametrize("index", [False])
@pytest.mark.parametrize("extension", [".ods", ".xls", ".xlsx"])
def test_loadspreadsheet_excel(
    tmp_path: Path,
    data_frame: pd.DataFrame,
    header: bool,
    index: bool,
    extension: str
):
    file_name = tmp_path / f"data{extension}"

    kwargs = dict()

    if extension == ".ods":
        kwargs["engine"] = "odf"

    data_frame.to_excel(file_name, header=header, index=index, sheet_name="sheet", **kwargs)

    spreadsheet = loadspreadsheet(file_name)

    if header:
        assert all(
            a == b
            for a, b in zip(data_frame.columns, spreadsheet.columns)
        )

    if index:
        assert all(
            a == b
            for a, b in zip(data_frame.index, spreadsheet.index)
        )


def test_loadspreadsheet_vest(tmp_path):
    file_name = tmp_path / "design.mat"

    with open(file_name, "w") as file_pointer:
        file_pointer.write(vest_str)

    spreadsheet = loadspreadsheet(file_name)

    assert spreadsheet.values.shape == (9, 2)
