# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def loadints(in_file):
    from halfpipe.io import loadmatrix

    return list(loadmatrix(in_file, dtype=int))


def ncol(in_file):
    import numpy as np

    array = np.loadtxt(in_file, ndmin=2)
    return array.shape[1]


def atleast_4d(ary):
    import numpy as np

    ary = np.atleast_3d(ary)

    if ary.ndim == 3:
        return ary[:, :, :, np.newaxis]

    else:
        return ary
