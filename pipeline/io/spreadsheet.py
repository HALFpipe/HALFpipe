# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import pandas as pd
from os import path as op


def load_spreadsheet(fname):
    try:
        ftype = op.splitext(fname)[1]
        if ftype == ".txt":
            df = pd.read_table(fname)
        elif ftype == ".json":
            df = pd.read_json(fname)
        elif ftype == ".csv":
            df = pd.read_csv(fname)
        elif ftype == ".xls":
            df = pd.read_excel(fname)
        elif ftype == ".ods":
            df = pd.read_excel(fname, engine="odf")
        else:
            df = pd.read_table(fname, sep=None)
        return df
    except Exception:
        pass
