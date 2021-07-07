# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import nibabel as nib

from .flame1 import calcgam, solveforbeta, flame1_prepare_data
from .base import ModelAlgorithm
from .miscmaths import chisq2z_convert


def calc_i2(y, z, s):
    """
    Chen et al. 2012
    """

    b = y
    x = z
    w0 = np.diag(1.0 / np.ravel(s))

    n, p = x.shape

    w0x = w0 @ x
    hat = np.linalg.lstsq(x.T @ w0x, w0x.T, rcond=None)[0]
    a0 = hat @ b

    r = b - x @ a0
    q = r.T @ w0 @ r

    p0 = w0 - w0x @ hat

    trp0 = np.trace(p0)

    τ2 = (q - (n - p - 1)) / trp0
    if τ2 < 0:
        τ2 = 0

    h2 = τ2 * trp0 / (n - p - 1) + 1

    h = np.sqrt(h2)

    i2 = float((h2 - 1) / h2)

    return h, i2


def log_prob(ex, y, z, s):
    try:
        gam, iU, _ = calcgam(ex, y, z, s)
    except np.linalg.LinAlgError:
        return -1e32

    npts = y.size

    r = y - z @ gam

    _, iU_logdet = np.linalg.slogdet(iU)

    he = float(r.T @ iU @ r)

    ret = -0.5 * npts * np.log(2 * np.pi) + 0.5 * float(iU_logdet) - 0.5 * he

    return ret


def heterogeneity_onvoxel(y, z, s):
    norm = np.std(y)
    y /= norm
    s /= np.square(norm)

    assert not np.any(s < 0), "Variance needs to be non-negative"

    ll_fe = log_prob(0, y, z, s)

    beta = solveforbeta(y, z, s)  # flame1 model fit
    ll_me = log_prob(beta, y, z, s)

    chisq = -2.0 * (ll_fe - ll_me)
    if abs(chisq) > 1e10:  # convergence failure
        return

    zstat = chisq2z_convert(chisq, 1)

    pseudor2 = 1 - ll_me / ll_fe
    if pseudor2 < 0:  # ensure range
        pseudor2 = 0
    elif pseudor2 > 1:
        pseudor2 = 1

    h, i2 = calc_i2(y, z, s)

    return beta, h, i2, pseudor2, chisq, zstat


class Heterogeneity(ModelAlgorithm):
    model_outputs = ["hbeta", "h", "i2", "hpseudor2", "hchisq", "hz"]
    contrast_outputs = []

    @staticmethod
    def voxel_calc(
        coordinate: Tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: Dict,
    ) -> Optional[Dict]:
        y, z, s = flame1_prepare_data(y, z, s)

        try:
            voxel_tuple = heterogeneity_onvoxel(y, z, s)

            if voxel_tuple is None:
                return
        except np.linalg.LinAlgError:
            return

        hbeta, h, i2, pseudor2, chisq, zstat = voxel_tuple
        voxel_dict: Dict[str, float] = dict(
            hbeta=hbeta, h=h, i2=i2, hpseudor2=pseudor2, hchisq=chisq, hz=zstat,
        )

        voxel_result = {coordinate: voxel_dict}
        return voxel_result

    @classmethod
    def write_outputs(cls, ref_img: nib.Nifti1Image, cmatdict: Dict, voxel_results: Dict) -> Dict:
        output_files = dict()

        rdf = pd.DataFrame.from_records(voxel_results)

        for map_name, series in rdf.iterrows():
            fname = cls.write_map(ref_img, map_name, series)
            output_files[map_name] = str(fname)

        return output_files
