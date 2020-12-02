# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import os
from pathlib import Path
from multiprocessing import get_context
from contextlib import nullcontext

import numpy as np
import pandas as pd
import nibabel as nib
from scipy import optimize

from nilearn.image import new_img_like

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    isdefined,
    File,
    InputMultiPath,
    SimpleInterface
)

from ...io import parse_design
from ..stats import DesignSpec
from .miscmaths import t2z_convert, f2z_convert

ctx = get_context("forkserver")


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

    assert not np.any(s < 0), "Variance needs to be non-negative"

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

        mask = np.isfinite(z)

        return dict(cope=cope, varcope=varcope, tdof=tdoflower, tstat=t, zstat=z, mask=mask)

    elif n > 1:
        fdof1 = n

        fdof2lower = npts - nevs

        f, z = f_ols_contrast(mn, covariance, fdof1, fdof2lower, cmat)

        mask = np.isfinite(z)

        return dict(fstat=f, fdof1=fdof1, fdof2=fdof2lower, zstat=z, mask=mask)


def voxel_calc(voxel_data):
    c, y, z, s, cmatdict = voxel_data

    npts = y.size

    try:
        mn, covariance = flame_stage1_onvoxel(y, z, s)
    except np.linalg.LinAlgError:
        return

    voxel_result = dict()

    for name, cmat in cmatdict.items():
        try:
            r = flame1_contrast(mn, covariance, npts, cmat)

            if name not in voxel_result:
                voxel_result[name] = dict()

            voxel_result[name][c] = r
        except np.linalg.LinAlgError:
            continue

    return voxel_result


def flame1(cope_files, mask_files, regressors, contrasts, var_cope_files=None, n_procs=1):

    # load data
    cope_data = [
        nib.load(f).get_fdata()[:, :, :, np.newaxis] for f in cope_files
    ]
    copes = np.concatenate(cope_data, axis=3)

    mask_data = [
        np.asanyarray(nib.load(f).dataobj).astype(np.bool)[:, :, :, np.newaxis]
        for f in mask_files
    ]
    masks = np.concatenate(mask_data, axis=3)

    if var_cope_files is not None:
        var_cope_data = [
            nib.load(f).get_fdata()[:, :, :, np.newaxis] for f in var_cope_files
        ]
        var_copes = np.concatenate(var_cope_data, axis=3)
    else:
        var_copes = np.zeros_like(copes)

    shape = copes[..., 0].shape

    dmat, cmatdict = parse_design(regressors, contrasts)

    nevs = dmat.columns.size

    masks = np.logical_and(masks, np.isfinite(copes))
    masks = np.logical_and(masks, np.isfinite(var_copes))
    masks = np.logical_and(masks, dmat.notna().all(axis=1))

    # prepare voxelwise
    def gen_voxel_data():
        def ensure_row_vector(x):
            return np.ravel(x)[:, np.newaxis]

        for c in np.ndindex(*shape):
            m = masks[c]
            npts = np.count_nonzero(m)

            if npts < nevs + 1:  # need at least one degree of freedom
                continue

            y = ensure_row_vector(copes[c][m])
            s = ensure_row_vector(var_copes[c][m])
            z = dmat.loc[m, :].to_numpy(dtype=np.float64)

            yield c, y, z, s, cmatdict

    prev_os_environ = os.environ.copy()
    os.environ.update({
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
    })

    voxel_data = gen_voxel_data()
    if n_procs < 2:
        cm = nullcontext()
        it = map(voxel_calc, voxel_data)
    else:
        cm = ctx.Pool(processes=n_procs)
        it = cm.imap_unordered(voxel_calc, voxel_data)

    # run voxelwise
    voxel_results = dict()
    with cm:
        for x in it:
            if x is None:
                continue

            for k, v in x.items():
                if k not in voxel_results:
                    voxel_results[k] = dict()

                voxel_results[k].update(v)

    os.environ.update(prev_os_environ)

    output_files = dict()

    # write outputs
    for output_name in ["copes", "var_copes", "tdof", "zstats", "tstats", "fstats", "masks"]:
        output_files[output_name] = [False for _ in range(len(voxel_results))]

    ref_img = nib.load(cope_files[0])

    for i, contrast_name in enumerate(cmatdict.keys()):  # cmatdict is ordered
        rdf = pd.DataFrame.from_records(voxel_results[contrast_name])

        for stat_name, series in rdf.iterrows():
            coordinates = series.index.to_list()
            values = series.values

            if stat_name == "mask":
                arr = np.zeros(shape, dtype=np.bool)

            else:
                arr = np.full(shape, np.nan)

            arr[(*zip(*coordinates),)] = values

            img = new_img_like(ref_img, arr, copy_header=True)

            fname = Path.cwd() / f"{stat_name}_{i+1}_{contrast_name}.nii.gz"
            nib.save(img, fname)

            if stat_name in ["tdof"]:
                output_name = stat_name

            else:
                output_name = f"{stat_name}s"

            if output_name in output_files:
                output_files[output_name][i] = fname

    return output_files


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

    n_procs = traits.Int(1, usedefault=True)


class FLAME1OutputSpec(TraitedSpec):
    copes = traits.List(
        traits.Either(File(exists=True), traits.Bool)
    )
    var_copes = traits.List(
        traits.Either(File(exists=True), traits.Bool)
    )
    tdof = traits.List(
        traits.Either(File(exists=True), traits.Bool)
    )
    zstats = traits.List(
        traits.Either(File(exists=True), traits.Bool)
    )
    fstats = traits.List(
        traits.Either(File(exists=True), traits.Bool)
    )
    tstats = traits.List(
        traits.Either(File(exists=True), traits.Bool)
    )
    masks = traits.List(
        traits.Either(File(exists=True), traits.Bool)
    )


class FLAME1(SimpleInterface):
    input_spec = FLAME1InputSpec
    output_spec = FLAME1OutputSpec

    def _run_interface(self, runtime):
        var_cope_files = self.inputs.var_cope_files

        if not isdefined(var_cope_files):
            var_cope_files = None

        self._results.update(
            flame1(
                cope_files=self.inputs.cope_files,
                var_cope_files=var_cope_files,
                mask_files=self.inputs.mask_files,
                regressors=self.inputs.regressors,
                contrasts=self.inputs.contrasts,
                n_procs=self.inputs.n_procs,
            )
        )

        return runtime
