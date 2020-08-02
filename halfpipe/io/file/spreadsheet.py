# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import logging
from functools import lru_cache

import numpy as np
import pandas as pd

from ...utils import splitext


@lru_cache(maxsize=128)
def loadspreadsheet(fname, ftype=None):
    try:
        if ftype is None:
            _, ftype = splitext(fname)
        if ftype == ".txt":
            df = pd.read_table(fname)
        elif ftype == ".json":
            df = pd.read_json(fname)
        elif ftype == ".csv":
            df = pd.read_csv(fname)
        elif ftype == ".tsv":
            df = pd.read_csv(fname, sep="\t")
        elif ftype == ".xls":
            df = pd.read_excel(fname)
        elif ftype == ".ods":
            df = pd.read_excel(fname, engine="odf")
        else:
            df = pd.read_table(fname, sep=None)
        return df
    except Exception:
        pass


@lru_cache(maxsize=128)
def loadmatrix(in_file, dtype=float):
    try:
        in_array = np.genfromtxt(in_file, missing_values="NaN,n/a,NA")
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, skip_header=1, missing_values="NaN,n/a,NA")
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, delimiter=",", missing_values="NaN,n/a,NA")
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, delimiter=",", skip_header=1, missing_values="NaN,n/a,NA")
        if not np.all(np.isnan(in_array)) and in_array.size > 0:
            return in_array.astype(dtype)
    except ValueError as e:
        logging.getLogger("halfpipe").exception(f"Could not load file {in_file}", e)
        raise
