# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from collections import OrderedDict
from pathlib import Path
import multiprocessing as mp

import numpy as np
import pandas as pd
import nibabel as nib
from scipy import optimize

from tqdm import tqdm

from nilearn.image import new_img_like

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    File,
    InputMultiPath,
    OutputMultiPath,
    SimpleInterface
)

from ...io import parse_design
from ..stats import DesignSpec
from .miscmaths import t2z_convert, f2z_convert

mp_context = mp.get_context("forkserver")


def calcgam(beta, y, z, s):
    weights = s + beta

    iU = np.diag(1.0 / np.ravel(weights))

    tmp = z.T @ iU
    ziUz = tmp @ z

    gamcovariance = np.linalg.inv(ziUz)
    gam = gamcovariance @ tmp @ y

    return gam, gamcovariance, iU, ziUz


def marg_posterior_energy(x, y, z, s):
    ex = np.exp(x)  # ex is variance

    if ex < 0 or np.isclose(ex, 0):
        return np.inf  # this 1e32 in the original code

    try:
        gam, _, iU, ziUz = calcgam(ex, y, z, s)
    except np.linalg.LinAlgError:
        return np.inf

    _, iU_logdet = np.linalg.slogdet(iU)
    _, ziUz_logdet = np.linalg.slogdet(ziUz)

    ret = -(
        0.5 * iU_logdet - 0.5 * ziUz_logdet
        - 0.5 * float(y.T @ iU @ y - gam.T @ ziUz @ gam)
    )

    return ret


def solveforbeta(y, z, s):
    res = optimize.minimize_scalar(
        marg_posterior_energy, args=(y, z, s), method="brent"
    )
    fu = res.x

    beta = max(1e-10, np.exp(fu))

    return beta


def flame_stage1_onvoxel(y, z, s):
    norm = np.std(y)
    y /= norm
    s /= np.square(norm)

    assert np.all(s > 0)  # variance needs to be positive

    beta = solveforbeta(y, z, s)

    gam, gamcovariance, _, _ = calcgam(beta, y, z, s)

    gam *= norm
    gamcovariance *= np.square(norm)

    return gam, gamcovariance


def t_ols_contrast(mn, covariance, dof, tcontrast):
    varcope = float(
        tcontrast @ covariance @ tcontrast.T
    )

    cope = float(tcontrast @ mn)

    if np.isnan(cope) or np.isnan(varcope) or np.isclose(varcope, 0) or varcope < 0:
        t = np.nan  # avoid warnings

    else:
        t = cope / np.sqrt(varcope)

    z = t2z_convert(t, dof)

    return cope, varcope, t, z


def f_ols_contrast(mn, covariance, dof1, dof2, fcontrast):
    f = float(mn.T @ fcontrast.T @ np.linalg.inv(fcontrast @ covariance @ fcontrast.T) @ fcontrast @ mn / dof1)

    z = f2z_convert(f, dof1, dof2)

    return f, z


def flame1_contrast(mn, covariance, npts, cmat):
    nevs = len(mn)

    n, _ = cmat.shape

    if n == 1:
        tdoflower = npts - nevs
        cope, varcope, t, z = t_ols_contrast(mn, covariance, tdoflower, cmat)

        return dict(cope=cope, varcope=varcope, tdof=tdoflower, t=t, zstat=z)

    elif n > 1:
        fdof1 = n

        fdof2lower = npts - nevs

        f, z = f_ols_contrast(mn, covariance, fdof1, fdof2lower, cmat)

        return dict(f=f, fdof1=fdof1, fdof2=fdof2lower, zstat=z)


class FLAME1InputSpec(DesignSpec):
    cope_files = InputMultiPath(
        File(exists=True),
        mandatory=True,
    )
    var_cope_files = InputMultiPath(
        File(exists=True),
        mandatory=False,
    )
    mask_files = InputMultiPath(
        File(exists=True),
        mandatory=True,
    )

    n_procs = traits.Int(default_value=1)


class FLAME1OutputSpec(TraitedSpec):
    copes = OutputMultiPath(
        File(exists=True), desc="Contrast estimates for each contrast"
    )
    var_copes = OutputMultiPath(
        File(exists=True), desc="Variance estimates for each contrast"
    )
    tdofs = OutputMultiPath(
        File(exists=True), desc="temporal dof file for each contrast"
    )
    zstats = OutputMultiPath(
        File(exists=True), desc="z-stat file for each contrast"
    )


class FLAME1(SimpleInterface):
    input_spec = FLAME1InputSpec
    output_spec = FLAME1OutputSpec

    def _run_interface(self, runtime):
        cope_files = self.inputs.cope_files
        var_cope_files = self.inputs.var_cope_files
        mask_files = self.inputs.mask_files

        cope_data = [
            nib.load(f).get_fdata()[:, :, :, np.newaxis] for f in cope_files
        ]
        var_cope_data = [
            nib.load(f).get_fdata()[:, :, :, np.newaxis] for f in var_cope_files
        ]
        mask_data = [
            np.asanyarray(nib.load(f).dataobj).astype(np.bool)[:, :, :, np.newaxis]
            for f in mask_files
        ]

        copes = np.concatenate(cope_data, axis=3)
        var_copes = np.concatenate(var_cope_data, axis=3)
        masks = np.concatenate(mask_data, axis=3)

        shape = copes[..., 0].shape

        dmat, cmatdict = parse_design(self.inputs.regressors, self.inputs.contrasts)

        nevs = dmat.columns.size

        res = OrderedDict((name, dict()) for name in cmatdict.keys())

        masks = np.logical_and(masks, np.isfinite(copes))
        masks = np.logical_and(masks, np.isfinite(var_copes))
        masks = np.logical_and(masks, dmat.notna().all(axis=1))

        # import pdb; pdb.set_trace()

        def ensure_row_vector(x):
            return np.ravel(x)[:, np.newaxis]

        with tqdm(total=np.prod(shape), unit="voxels") as pbar:
            for c in np.ndindex(*shape):
                pbar.update()

                m = masks[c]
                npts = np.count_nonzero(m)

                if npts < nevs + 1:  # need at least one degree of freedom
                    continue

                y = ensure_row_vector(copes[c][m])
                s = ensure_row_vector(var_copes[c][m])
                z = dmat.loc[m, :].to_numpy(dtype=np.float64)

                try:
                    mn, covariance = flame_stage1_onvoxel(y, z, s)
                except np.linalg.LinAlgError:
                    continue

                for name, cmat in cmatdict.items():
                    try:
                        r = flame1_contrast(mn, covariance, npts, cmat)

                        res[name][c] = r
                    except np.linalg.LinAlgError:
                        continue

        for stat_name in ["cope", "var_cope", "tdof", "zstat"]:
            self._results[f"{stat_name}s"] = [False for _ in range(len(res))]

        ref_img = nib.load(cope_files[0])

        for i, (contrast_name, r) in enumerate(res.items()):
            rdf = pd.DataFrame.from_records(r)

            for stat_name, series in rdf.iterrows():
                coordinates = series.index.to_list()
                values = series.values

                arr = np.full(shape, np.nan)
                arr[(*zip(*coordinates),)] = values

                img = new_img_like(ref_img, arr, copy_header=True)

                fname = Path.cwd() / f"{stat_name}_{i+1}_{contrast_name}.nii.gz"
                nib.save(img, fname)

                if f"{stat_name}s" in self._results:
                    self._results[f"{stat_name}s"][i] = fname
