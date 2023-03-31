# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def deepcopyfactory(obj):
    import pickle

    s = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    return lambda: pickle.loads(s)


def deepcopy(obj):
    from halfpipe.utils.copy import deepcopyfactory

    return deepcopyfactory(obj)()
