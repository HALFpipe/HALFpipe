# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict

import numpy as np
import pandas as pd
from numpy import typing as npt


def parse_design(
    regressors: dict[str, list[float]], contrasts: list[tuple]
) -> tuple[pd.DataFrame, OrderedDict[str, npt.NDArray]]:
    design_matrix = pd.DataFrame.from_dict(regressors)

    contrast_matrices: OrderedDict[str, npt.NDArray] = OrderedDict()

    def make_contrast_matrix(conditions, weights) -> npt.NDArray:
        contrast_matrix = pd.Series(data=weights, index=conditions)[
            design_matrix.columns
        ]
        return contrast_matrix.to_numpy(dtype=np.float64)[np.newaxis, :]

    for contrast in contrasts:
        name = contrast[0]
        statistic = contrast[1]

        contrast_matrix = None

        if statistic == "F":
            child_contrast_matrices = list()

            for child_contrast_name, _, conditions, weights in contrast[2]:
                child_contrast_matrix = make_contrast_matrix(conditions, weights)

                if child_contrast_name in contrast_matrices:
                    assert np.allclose(
                        contrast_matrices[child_contrast_name], child_contrast_matrix
                    )
                    del contrast_matrices[child_contrast_name]

                child_contrast_matrices.append(child_contrast_matrix)

            contrast_matrix = np.concatenate(child_contrast_matrices, axis=0)

        elif statistic == "T":
            conditions, weights = contrast[2:]
            contrast_matrix = make_contrast_matrix(conditions, weights)

        if contrast_matrix is not None:
            contrast_matrices[name] = contrast_matrix

    return design_matrix, contrast_matrices
