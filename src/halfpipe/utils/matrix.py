# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def load_vector(in_file):
    from halfpipe.ingest.spreadsheet import read_spreadsheet
    from halfpipe.utils.ops import ravel

    return ravel(read_spreadsheet(in_file).values)


def ncol(in_file):
    import numpy as np

    array = np.loadtxt(in_file, ndmin=2)
    return array.shape[1]


def atleast_4d(array):
    import numpy as np

    array = np.atleast_3d(array)

    if array.ndim == 3:
        return array[:, :, :, np.newaxis]

    else:
        return array
