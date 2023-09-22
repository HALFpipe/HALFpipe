# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import warnings

import numpy as np
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import (
    PerfectSeparationError,
    PerfectSeparationWarning,
)

from .base import demean
from .heterogeneity import Heterogeneity
from .miscmaths import chisq2z_convert


class MCARTest(Heterogeneity):
    model_outputs = ["mcarchisq", "mcardof", "mcarz"]
    contrast_outputs: list[str] = []

    @staticmethod
    def voxel_calc(
        coordinate: tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: dict,
    ) -> dict | None:
        z = demean(z)

        is_available = np.isfinite(y) & np.isfinite(s)
        is_missing = ~is_available

        if np.all(is_missing) or np.all(is_available):
            return None  # zero variance

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                # Treat perfect separation as an error
                warnings.simplefilter("error", PerfectSeparationWarning)
                model = sm.Logit(is_missing.ravel().astype(float), z, missing="drop")
                result = model.fit(disp=False, warn_convergence=False)

                chisq = result.llr
                dof = result.df_model
            zstat = chisq2z_convert(chisq, dof)

            voxel_dict = dict(mcarchisq=chisq, mcardof=dof, mcarz=zstat)
            voxel_result = {coordinate: voxel_dict}
            return voxel_result
        except (
            PerfectSeparationError,
            PerfectSeparationWarning,
            np.linalg.LinAlgError,
        ):
            return None
