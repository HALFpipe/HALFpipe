# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from functools import lru_cache
import warnings
import re

import numpy as np
import pandas as pd
import chardet

from ...utils import splitext


def find_encoding(fname):
    with open(fname, "rb") as csvfile:
        data = csvfile.read(1024)
    return chardet.detect(data)["encoding"]


def has_header(fname, encoding=None):
    if encoding is None:
        encoding = find_encoding(fname)
    with open(fname, "r", encoding=encoding) as csvfile:
        data = csvfile.read(1024)
    data = re.sub(r"[^\x00-\x7f]", "", data)  # remove unicode characters, e.g. BOM
    if data.startswith("/"):  # fsl vest formal
        return False
    if re.match(r"^\s*[\'\"]?[a-zA-Z]+", data) is not None:
        return True
    return False  # default


@lru_cache(maxsize=128)
def loadspreadsheet(fname, dtype=None, ftype=None, **kwargs) -> pd.DataFrame:
    df = None

    if ftype is None:
        _, ftype = splitext(fname)

    kwargs.update(dict(
        dtype=dtype,
    ))

    encoding = None
    if ftype not in [".xls", ".xlsx", ".ods"]:
        encoding = find_encoding(fname)
        kwargs.update(dict(encoding=encoding))

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        try:
            if ftype in [".xls", ".xlsx"]:
                df = pd.read_excel(fname, **kwargs)

            elif ftype == ".ods":
                df = pd.read_excel(fname, engine="odf", **kwargs)

            elif ftype == ".json":
                df = pd.read_json(fname, **kwargs)

            else:  # some kind of delimited format
                table_args = dict(**kwargs)
                if not has_header(fname, encoding=encoding):
                    table_args.update(dict(header=None))

                if ftype == ".txt":
                    df = pd.read_table(fname, delim_whitespace=True, **table_args)
                elif ftype == ".csv":
                    df = pd.read_csv(fname, **table_args)
                elif ftype == ".tsv":
                    df = pd.read_csv(fname, sep="\t", **table_args)
                else:  # infer delimiter
                    df = pd.read_table(fname, sep=None, engine="python", **table_args)

        except Exception:
            df = pd.DataFrame(loadmatrix(fname, **kwargs))

    assert isinstance(df, pd.DataFrame)
    return df


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
