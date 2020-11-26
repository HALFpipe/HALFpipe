# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
import nibabel as nib
from scipy import optimize

from nilearn.image import new_img_like

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    File,
    InputMultiPath,
    OutputMultiPath,
    SimpleInterface
)

from .miscmaths import t2z_convert, f2z_convert


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

    if ex <= 0:
        return np.inf  # this 1e32 in the original code

    gam, _, iU, ziUz = calcgam(ex, y, z, s)

    _, iU_logdet = np.linalg.slogdet(iU)
    _, ziUz_logdet = np.linalg.slogdet(ziUz)

    ret = -(
        0.5 * iU_logdet - 0.5 * ziUz_logdet
        - 0.5 * np.asscalar(y.T @ iU @ y - gam.T @ ziUz @ gam)
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
    varcope = np.asscalar(
        tcontrast @ covariance @ tcontrast.T
    )

    cope = np.asscalar(tcontrast @ mn)

    t = cope / np.sqrt(varcope)
    z = t2z_convert(t, dof)

    return cope, varcope, t, z


def f_ols_contrast(mn, covariance, dof1, dof2, fcontrast):
    f = np.asscalar(mn.T @ fcontrast.T @ np.linalg.inv(fcontrast @ covariance @ fcontrast.T) @ fcontrast @ mn / dof1)

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


class FLAME1InputSpec(TraitedSpec):
    cope_files = InputMultiPath(
        File(exists=True),
        mandatory=True,
    )
    var_cope_files = InputMultiPath(
        File(exists=True),
        mandatory=True,
    )
    mask_files = InputMultiPath(
        File(exists=True),
        mandatory=True,
    )

    regressors = traits.Dict(
        traits.Str,
        traits.List(traits.Float),
        mandatory=True,
    )
    contrasts = traits.List(
        traits.Either(
            traits.Tuple(traits.Str, traits.Enum("T"), traits.List(traits.Str),
                         traits.List(traits.Float)),
            traits.Tuple(traits.Str, traits.Enum("F"),
                         traits.List(
                             traits.Tuple(traits.Str, traits.Enum("T"),
                                          traits.List(traits.Str),
                                          traits.List(traits.Float)),
            ))
        ),
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

    def _parse_design(self):
        dmat = pd.DataFrame.from_dict(self.inputs.regressors)

        cmatdict = OrderedDict()

        def makecmat(conditions, weights):
            cmat = pd.Series(data=weights, index=conditions)[dmat.columns]
            cmat = cmat.to_numpy(dtype=np.float64)[np.newaxis, :]

            return cmat

        for contrast in self.inputs.contrasts:
            name, statistic, cdata = contrast

            cmat = None

            if statistic == "F":
                tcmats = list()

                for tname, _, conditions, weights in cdata:
                    tcmat = makecmat(conditions, weights)

                    if tname in cmatdict:
                        assert np.allclose(cmatdict[tname], tcmat)
                        del cmatdict[tname]

                    tcmats.append(tcmat)

                cmat = np.concatenate(tcmats, axis=0)

            elif statistic == "T":
                conditions, weights = cdata
                cmat = makecmat(conditions, weights)

            if cmat is not None:
                cmatdict[name] = cmat

        return dmat, cmatdict

    def _run_interface(self, runtime):
        cope_files = self.inputs.cope_files
        var_cope_files = self.inputs.var_cope_files
        mask_files = self.inputs.mask_files

        cope_data = [nib.load(f).get_fdata() for f in cope_files]
        var_cope_data = [nib.load(f).get_fdata() for f in var_cope_files]
        mask_data = [np.asanyarray(nib.load(f).dataobj).astype(np.bool) for f in mask_files]

        copes = np.concatenate(cope_data, axis=3)
        var_copes = np.concatenate(var_cope_data, axis=3)
        masks = np.concatenate(mask_data, axis=3)

        shape = copes[..., 0].shape

        dmat, cmatdict = self._parse_design()

        res = OrderedDict((name, dict()) for name in cmatdict.keys())

        def ensure_column_vector(x):
            return np.ravel(x)[np.newaxis, :]

        for c in np.ndindex(*shape):
            m = masks[c]
            m = np.logical_and(m, copes[c].isfinite())
            m = np.logical_and(m, var_copes[c].isfinite())
            m = np.logical_and(m, dmat.notna().all(axis=1))

            y = ensure_column_vector(copes[c][m])

            npts = len(y)

            if npts == 0:
                continue

            s = ensure_column_vector(var_copes[c][m])

            z = dmat.loc[m, :].to_numpy(dtype=np.float64)

            mn, covariance = flame_stage1_onvoxel(y, z, s)

            for name, cmat in cmatdict.items():
                r = flame1_contrast(mn, covariance, npts, cmat)

                res[name][c] = r

        for stat_name in ["cope", "var_cope", "tdof", "zstat"]:
            self._results[f"{stat_name}s"] = [None for _ in range(len(res))]

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
