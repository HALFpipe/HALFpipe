# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict

import numpy as np
import pandas as pd


def parse_design(regressors, contrasts):
    dmat = pd.DataFrame.from_dict(regressors)

    cmatdict = OrderedDict()

    def makecmat(conditions, weights):
        cmat = pd.Series(data=weights, index=conditions)[dmat.columns]
        cmat = cmat.to_numpy(dtype=np.float64)[np.newaxis, :]

        return cmat

    for contrast in contrasts:
        name = contrast[0]
        statistic = contrast[1]

        cmat = None

        if statistic == "F":
            tcmats = list()

            for tname, _, conditions, weights in contrast[2]:
                tcmat = makecmat(conditions, weights)

                if tname in cmatdict:
                    assert np.allclose(cmatdict[tname], tcmat)
                    del cmatdict[tname]

                tcmats.append(tcmat)

            cmat = np.concatenate(tcmats, axis=0)

        elif statistic == "T":
            conditions, weights = contrast[2:]
            cmat = makecmat(conditions, weights)

        if cmat is not None:
            cmatdict[name] = cmat

    return dmat, cmatdict
