# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from math import isclose, isfinite, isnan, nan
from typing import Any

import nibabel as nib
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from typing_extensions import Literal

from ..utils.format import format_workflow
from .base import ModelAlgorithm, demean, listwise_deletion
from .miscmaths import f2z_convert, t2z_convert


def calcgam(beta, y, z, s) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    weights = s + beta

    iU = np.diag(1.0 / np.ravel(weights))

    tmp = z.T @ iU
    ziUz = tmp @ z

    gam = np.linalg.lstsq(ziUz, tmp @ y, rcond=None)[0]

    return gam, iU, ziUz


def marg_posterior_energy(ex, y, z, s):
    if ex < 0 or isclose(ex, 0.0):
        return 1e32  # very large value

    try:
        gam, iU, ziUz = calcgam(ex, y, z, s)
    except np.linalg.LinAlgError:
        return 1e32

    _, iU_logdet = np.linalg.slogdet(iU)
    _, ziUz_logdet = np.linalg.slogdet(ziUz)

    ret = -(
        0.5 * float(iU_logdet)
        - 0.5 * float(ziUz_logdet)
        - 0.5 * float(y.T @ iU @ y - gam.T @ ziUz @ gam)
    )

    return ret


def solveforbeta(y, z, s):
    res = minimize_scalar(marg_posterior_energy, args=(y, z, s), method="brent")
    fu = res.x

    beta = max(1e-10, fu)

    return beta


def flame_stage1_onvoxel(y, z, s):
    norm = np.std(y)
    y /= norm
    s /= np.square(norm)

    assert not np.any(s < 0), "Variance needs to be non-negative"

    beta = solveforbeta(y, z, s)

    gam, _, ziUz = calcgam(beta, y, z, s)

    gam *= norm
    ziUz /= np.square(norm)

    return gam, ziUz


def t_ols_contrast(mn, inverse_covariance, dof, tcontrast):
    a = np.linalg.lstsq(inverse_covariance, tcontrast.T, rcond=None)[0]
    varcope = float(tcontrast @ a)

    cope = float(tcontrast @ mn)

    if isnan(cope) or isnan(varcope) or isclose(varcope, 0) or varcope < 0:
        t = np.nan  # avoid warnings

    else:
        t = cope / np.sqrt(varcope)

    z = t2z_convert(t, dof)

    return cope, varcope, t, z


def f_ols_contrast(mn, inverse_covariance, dof1, dof2, fcontrast):
    cope = fcontrast @ mn

    a = fcontrast @ np.linalg.lstsq(inverse_covariance, fcontrast.T, rcond=None)[0]
    b = np.linalg.lstsq(a, cope, rcond=None)[0]

    f = float(cope.T @ b) / dof1

    z = f2z_convert(f, dof1, dof2)

    return cope, f, z


def flame1_contrast(mn, inverse_covariance, npts, cmat):
    nevs = len(mn)

    n, _ = cmat.shape

    if n == 1:
        tdoflower = npts - nevs
        cope, varcope, t, z = t_ols_contrast(mn, inverse_covariance, tdoflower, cmat)

        mask = isfinite(z)

        return dict(
            cope=cope, var_cope=varcope, dof=tdoflower, tstat=t, zstat=z, mask=mask
        )

    elif n > 1:
        fdof1 = n

        fdof2lower = npts - nevs

        cope, f, z = f_ols_contrast(mn, inverse_covariance, fdof1, fdof2lower, cmat)

        mask = isfinite(z)

        return dict(cope=cope, fstat=f, dof=[fdof1, fdof2lower], zstat=z, mask=mask)


def flame1_prepare_data(y: np.ndarray, z: np.ndarray, s: np.ndarray):
    # filtering for design matrix is already done
    # the nans that are left should be replaced with zeros
    z = np.nan_to_num(z)

    # remove observations with nan cope/varcope
    y, z, s = listwise_deletion(y, z, s)

    # finally demean the design matrix
    z = demean(z)

    return y, z, s


class FLAME1(ModelAlgorithm):
    model_outputs: list[str] = []
    contrast_outputs = [
        "copes",
        "var_copes",
        "zstats",
        "tstats",
        "fstats",
        "dof",
        "masks",
    ]

    @staticmethod
    def voxel_calc(
        coordinate: tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: dict,
    ) -> dict | None:
        y, z, s = flame1_prepare_data(y, z, s)

        npts = y.size

        try:
            mn, inverse_covariance = flame_stage1_onvoxel(y, z, s)
        except np.linalg.LinAlgError:
            return None

        voxel_result: dict[str, dict[tuple[int, int, int], Any]] = defaultdict(dict)

        for name, cmat in cmatdict.items():
            try:
                r = flame1_contrast(mn, inverse_covariance, npts, cmat)
                voxel_result[name][coordinate] = r
            except np.linalg.LinAlgError:
                continue

        return voxel_result

    @classmethod
    def write_outputs(
        cls, ref_img: nib.Nifti1Image, cmatdict: dict, voxel_results: dict
    ) -> dict:
        output_files: dict[str, list[Literal[False] | str]] = dict()

        for output_name in cls.contrast_outputs:
            output_files[output_name] = [False] * len(cmatdict)

        for i, contrast_name in enumerate(cmatdict.keys()):  # cmatdict is ordered
            contrast_results = voxel_results[contrast_name]

            rdf = pd.DataFrame.from_records(contrast_results)

            if "mask" not in rdf.index:  # ensure that we always output a mask
                rdf = rdf.append(pd.Series(data=False, index=rdf.columns, name="mask"))

            if "zstat" not in rdf.index:  # ensure that we always output a zstat
                rdf = rdf.append(pd.Series(data=nan, index=rdf.columns, name="zstat"))

            for map_name, series in rdf.iterrows():
                out_name = f"{map_name}_{i+1}_{format_workflow(contrast_name)}"
                fname = cls.write_map(ref_img, out_name, series)

                if map_name in frozenset(["dof"]):
                    output_name = map_name

                else:
                    output_name = f"{map_name}s"

                if output_name in output_files:
                    output_files[output_name][i] = str(fname)

        return output_files
