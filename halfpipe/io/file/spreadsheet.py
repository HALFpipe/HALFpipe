# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from functools import lru_cache
import csv

import numpy as np
import pandas as pd

from ...utils import splitext


def has_header(fname):
    with open(fname, newline="") as csvfile:
        data = csvfile.read(1024)
        if data.startswith("/"):
            return False
        try:
            return csv.Sniffer().has_header(data)
        except Exception:
            return False  # default


@lru_cache(maxsize=128)
def loadspreadsheet(fname, ftype=None):
    df = None
    try:
        if ftype is None:
            _, ftype = splitext(fname)
        if ftype == ".txt":
            df = pd.read_table(fname)
        elif ftype == ".json":
            df = pd.read_json(fname)
        elif ftype == ".csv":
            if not has_header(fname):
                df = pd.read_csv(fname, header=None)
            else:
                df = pd.read_csv(fname)
        elif ftype == ".tsv":
            if not has_header(fname):
                df = pd.read_csv(fname, sep="\t", header=None)
            else:
                df = pd.read_csv(fname, sep="\t")
        elif ftype == ".xls":
            df = pd.read_excel(fname)
        elif ftype == ".ods":
            df = pd.read_excel(fname, engine="odf")
        else:
            df = pd.read_table(fname, sep=None, engine="python")
        if df is not None:
            return df
    except Exception:
        pass
    df = pd.DataFrame(loadmatrix(fname))
    return df


@lru_cache(maxsize=128)
def loadmatrix(in_file, dtype=float, **kwargs):
    kwargs = dict(**kwargs, missing_values="NaN,n/a,NA", autostrip=True)
    try:
        in_array = np.genfromtxt(in_file, **kwargs)
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, skip_header=1, **kwargs)
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, delimiter=",", **kwargs)
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, delimiter=",", skip_header=1, **kwargs)
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError:
        pass
    return loadmatrix(in_file, dtype=dtype, comments="/")
