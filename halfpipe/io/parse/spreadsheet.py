# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import Optional

from functools import lru_cache
import warnings
import re
import csv
import io
from statistics import mean

import numpy as np
import pandas as pd
import chardet

from ...utils import splitext


def str_is_convertible_to_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


@lru_cache(maxsize=1024)
def loadspreadsheet(file_name, extension=None, **kwargs) -> pd.DataFrame:
    if extension is None:
        _, extension = splitext(file_name)

    with open(file_name, "rb") as file_pointer:
        file_bytes: bytes = file_pointer.read()

    if extension in [".xls", ".xlsx"]:
        file_io = io.BytesIO(file_bytes)
        return pd.read_excel(file_io, **kwargs)

    elif extension == ".ods":
        file_io = io.BytesIO(file_bytes)
        return pd.read_excel(file_io, engine="odf", **kwargs)

    else:
        encoding = chardet.detect(file_bytes)["encoding"]
        kwargs["encoding"] = encoding

        file_str = file_bytes.decode(encoding)

        if extension == ".json":
            file_io = io.StringIO(file_str)
            return pd.read_json(file_io, typ="frame", **kwargs)

        else:
            cleaned_file_str = re.sub(
                r"[^\x00-\x7f]", "", file_str
            )  # remove unicode characters, e.g. BOM
            file_lines = cleaned_file_str.splitlines()

            file_lines = [
                s for s in file_lines if len(s.strip()) > 0
            ]

            comment_prefix: Optional[str] = None
            comment_m = re.match(
                r"^(?P<prefix>[£$%^#/\\]+)", file_lines[0]
            )  # detect prefix only at start of file
            if comment_m is not None:
                comment_prefix = comment_m.group("prefix")

            if comment_prefix is not None:
                file_lines = [
                    s for s in file_lines if not s.startswith(comment_prefix)
                ]

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
                    mean(map(float, map(
                        str_is_convertible_to_float,
                        re.split(kwargs["sep"], file_line)
                    )))
                    for file_line in file_lines[:10]
                ]
                if min(scores[1:]) > 0.:
                    # check if there are at least some float values, without
                    # which this heuristic would be pointless
                    if scores[0] >= min(scores[1:]):
                        # the first line does not have a lower amount of floats
                        # than subsequent lines
                        kwargs["header"] = None

            file_io = io.StringIO(cleaned_file_str)
            data_frame = pd.read_csv(file_io, engine="python", **kwargs)

            data_frame.columns = [
                s.strip() if isinstance(s, str) else s
                for s in data_frame.columns
            ]

            if data_frame.columns[0] == "Unnamed: 0":
                # detect index_col that pandas may have missed
                if not any(
                        isinstance(s, float)
                        or (
                            isinstance(s, str)
                            and str_is_convertible_to_float(s)
                        )
                        for s in data_frame["Unnamed: 0"]
                ):
                    data_frame.set_index("Unnamed: 0", inplace=True)
                    data_frame.index.rename(None, inplace=True)

            return data_frame


@lru_cache(maxsize=128)
def loadmatrix(in_file, dtype=float, **kwargs):
    kwargs.update(dict(missing_values="NaN,n/a,NA", autostrip=True))
    exception = ValueError()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            in_array = np.genfromtxt(in_file, **kwargs)
            if not np.all(np.isnan(in_array)) and in_array.size > 0:
                return in_array.astype(dtype)
        except Exception as e:
            exception = e
        try:
            in_array = np.genfromtxt(in_file, skip_header=1, **kwargs)
            if not np.all(np.isnan(in_array)) and in_array.size > 0:
                return in_array.astype(dtype)
        except Exception as e:
            exception = e
        try:
            in_array = np.genfromtxt(in_file, delimiter=",", **kwargs)
            if not np.all(np.isnan(in_array)) and in_array.size > 0:
                return in_array.astype(dtype)
        except Exception as e:
            exception = e
        try:
            in_array = np.genfromtxt(in_file, delimiter=",", skip_header=1, **kwargs)
            if not np.all(np.isnan(in_array)) and in_array.size > 0:
                return in_array.astype(dtype)
        except Exception as e:
            exception = e
    if kwargs.get("comments") != "/":
        return loadmatrix(in_file, dtype=dtype, comments="/", **kwargs)
    raise exception
