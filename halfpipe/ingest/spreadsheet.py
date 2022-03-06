# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import csv
import io
import re
from statistics import mean

import chardet
import pandas as pd

from ..utils.path import split_ext


def str_is_convertible_to_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def read_spreadsheet(file_name, extension=None, **kwargs) -> pd.DataFrame:
    if extension is None:
        _, extension = split_ext(file_name)

    with open(file_name, "rb") as file_pointer:
        file_bytes: bytes = file_pointer.read()

    if len(file_bytes) == 0:
        # empty file means empty data frame
        return pd.DataFrame()

    elif extension in [".xls", ".xlsx"]:
        bytes_io = io.BytesIO(file_bytes)
        return pd.read_excel(bytes_io, **kwargs)

    elif extension == ".ods":
        bytes_io = io.BytesIO(file_bytes)
        return pd.read_excel(bytes_io, engine="odf", **kwargs)

    encoding = chardet.detect(file_bytes)["encoding"]

    if encoding is None:
        encoding = "utf8"

    kwargs["encoding"] = encoding

    file_str = file_bytes.decode(encoding)

    if extension == ".json":
        string_io = io.StringIO(file_str)
        data_frame = pd.read_json(string_io, typ="frame", **kwargs)
        assert isinstance(data_frame, pd.DataFrame)
        return data_frame

    cleaned_file_str = re.sub(
        r"[^\x00-\x7f]", "", file_str
    )  # remove unicode characters, e.g. BOM
    file_lines = cleaned_file_str.splitlines()

    file_lines = [s for s in file_lines if len(s.strip()) > 0]

    comment_prefix: str | None = None
    comment_m = re.match(
        r"^(?P<prefix>[£$%^#/\\]+)", file_lines[0]
    )  # detect prefix only at start of file
    if comment_m is not None:
        comment_prefix = comment_m.group("prefix")

    if comment_prefix is not None:
        file_lines = [s for s in file_lines if not s.startswith(comment_prefix)]

    cleaned_file_str = "\n".join(file_lines)

    dialect = None
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(cleaned_file_str)
    except csv.Error:
        pass

    if extension == ".tsv":
        kwargs["sep"] = "\t"

    elif extension == ".csv":
        kwargs["sep"] = "[,;]"

    if len(file_lines) == 0:
        # empty data frame
        return pd.DataFrame()

    elif len(file_lines) == 1 and str_is_convertible_to_float(file_lines[0]):
        # just a number in a file
        return pd.DataFrame([float(file_lines[0])])

    elif len(file_lines) == 2 and str_is_convertible_to_float(file_lines[1]):
        # a number with a column name in a file
        return pd.DataFrame(
            [float(file_lines[1])],
            columns=[file_lines[0].strip()],
        )

    if isinstance(kwargs.get("sep"), str):
        if kwargs["sep"] not in cleaned_file_str:
            del kwargs["sep"]

    if kwargs.get("sep") is None:
        if (
            dialect is not None
            and dialect.delimiter != " "  # single space should be \s+
            and re.match(r"[a-zA-Z0-9\.]", dialect.delimiter) is None  # ignore letters
        ):
            kwargs["sep"] = dialect.delimiter
        else:
            kwargs["sep"] = r"\s+"

    if len(file_lines) < 2:
        kwargs["header"] = None
    else:
        scores = [
            mean(
                map(
                    float,
                    map(
                        str_is_convertible_to_float, re.split(kwargs["sep"], file_line)
                    ),
                )
            )
            for file_line in file_lines[:10]
        ]
        if min(scores[1:]) > 0.0:
            # check if there are at least some float values, without
            # which this heuristic would be pointless
            if scores[0] >= min(scores[1:]):
                # the first line does not have a lower amount of floats
                # than subsequent lines
                kwargs["header"] = None

    string_io = io.StringIO(cleaned_file_str)
    data_frame = pd.read_csv(string_io, engine="python", **kwargs)
    assert isinstance(data_frame, pd.DataFrame)

    # data_frame.reset_index(inplace=True)  # restore detected index_col

    def strip_if_str(s):
        if isinstance(s, str):
            return s.strip()
        return s

    data_frame.rename(columns=strip_if_str, inplace=True)

    if data_frame.columns[0] == "Unnamed: 0":
        # detect index_col that pandas may have missed
        if not any(
            isinstance(s, float)
            or (isinstance(s, str) and str_is_convertible_to_float(s))
            for s in data_frame["Unnamed: 0"]
        ):
            data_frame.set_index("Unnamed: 0", inplace=True)
            data_frame.index.rename(None, inplace=True)

    return data_frame
