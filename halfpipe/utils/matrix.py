# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def loadints(in_file):
    from halfpipe.io import loadmatrix

    return list(loadmatrix(in_file, dtype=int))


def ncol(in_file):
    from halfpipe.io import loadmatrix

    array = loadmatrix(in_file)
    if array.ndim == 1:
        return 1
    return array.shape[1]
