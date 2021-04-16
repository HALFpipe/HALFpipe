# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from typing import Dict, Optional, Tuple

import numpy as np
import nibabel as nib
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import PerfectSeparationError

from .base import ModelAlgorithm
from .heterogeneity import Heterogeneity


class MCARTest(ModelAlgorithm):
    outputs = ["mcar", "mcardof"]

    @staticmethod
    def voxel_calc(
        coordinate: Tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: dict,
    ) -> Optional[Dict]:
        isavailable = np.logical_and(
            np.isfinite(y), np.isfinite(s)
        )
        ismissing = np.logical_not(isavailable)

        if np.all(ismissing) or np.all(isavailable):
            return  # zero variance

        model = sm.Logit(ismissing, z, missing="drop")

        try:
            result = model.fit(disp=False, warn_convergence=False)
        except (PerfectSeparationError, np.linalg.LinAlgError):
            return

        voxel_dict = dict(mcar=result.llr, mcardof=result.df_model)

        voxel_result = {coordinate: voxel_dict}
        return voxel_result

    @staticmethod
    def write_outputs(ref_img: nib.Nifti1Image, cmatdict: Dict, voxel_results: Dict) -> Dict:
        return Heterogeneity.write_outputs(ref_img, cmatdict, voxel_results)
