# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import inf, log, nan, pi

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import optimize, special, stats

from ..utils import logger
from .base import ModelAlgorithm
from .flame1 import flame1_prepare_data


class MoM:
    @staticmethod
    def i2(y, z, s):
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
        i2 = float((h2 - 1) / h2)

        return i2


class ReML:
    @staticmethod
    def model(ϑ: float, x: np.ndarray | None, s: np.ndarray):
        σg = ϑ

        if σg < 0:
            return None, None, None

        vinv = np.diag(np.ravel(1.0 / (s + σg)))

        if x is None:
            return vinv, None, None

        a = x.T @ vinv
        b = a @ x

        # projection matrix
        p = vinv - a.T @ np.linalg.lstsq(b, a, rcond=None)[0]
        return vinv, p, b

    @classmethod
    def fit(cls, y: np.ndarray, x: np.ndarray | None, s: np.ndarray):
        return optimize.minimize_scalar(cls.neg_log_lik, args=(y, x, s), method="brent")

    @classmethod
    def neg_log_lik(cls, ϑ: float, y: np.ndarray, x: np.ndarray | None, s: np.ndarray):
        vinv, p, b = cls.model(ϑ, x, s)

        if vinv is None:
            return inf

        _, log_det_vinv = np.linalg.slogdet(vinv)
        neg_log_lik = -float(log_det_vinv) / 2

        if p is None or b is None:
            return neg_log_lik

        _, log_det_xvinvx = np.linalg.slogdet(b)
        neg_log_lik += float(log_det_xvinvx) / 2

        neg_log_lik += float(y.T @ p @ y) / 2

        return neg_log_lik

    @classmethod
    def jacobian(cls, ϑ: float, y: np.ndarray, x: np.ndarray | None, s: np.ndarray):
        _, p, b = cls.model(ϑ, x, s)

        if p is None or b is None:
            return nan

        return float(np.trace(p) - y.T @ p @ p @ y)

    @classmethod
    def hessian(cls, ϑ: float, y: np.ndarray, x: np.ndarray | None, s: np.ndarray):
        _, p, b = cls.model(ϑ, x, s)

        if p is None or b is None:
            return nan

        return float(y.T @ p @ p @ p @ y)


class ML:
    @staticmethod
    def neg_log_lik(
        ϑ: float, y: np.ndarray, x: np.ndarray | None, s: np.ndarray, γ: np.ndarray
    ):
        σg = ϑ

        if σg < 0:
            return inf

        vinv = np.diag(np.ravel(1.0 / (s + σg)))

        n = y.size
        neg_log_lik = n * np.log(2 * pi) / 2

        _, log_det_vinv = np.linalg.slogdet(vinv)
        neg_log_lik += -float(log_det_vinv) / 2

        if x is None:
            return neg_log_lik

        r: np.ndarray = y - x @ γ
        neg_log_lik += float(r.T @ vinv @ r) / 2

        return neg_log_lik


class InvGammaML:
    @classmethod
    def fit(cls, x: np.ndarray):
        a, _, scale = stats.invgamma.fit(x, floc=0)
        ϑ = np.array([a, scale])

        return ϑ

    @staticmethod
    def neg_log_lik(ϑ: np.ndarray, x: np.ndarray):
        a, b = ϑ

        if a < 0 or b < 0:
            return inf

        n = x.size

        u = np.sum(np.log(x))
        v = np.sum(1 / x)

        return -n * a * log(b) + n * log(special.gamma(a)) + a * u + u + b * v

    @staticmethod
    def jacobian(ϑ: np.ndarray, x: np.ndarray):
        a, b = ϑ

        if a < 0 or b < 0:
            return np.array([nan] * 2)

        n = x.size

        u = np.sum(np.log(x))
        v = np.sum(1 / x)

        return np.array(
            [
                -n * log(b) + n * special.digamma(a) + u,
                -n * a / b + v,
            ]
        )

    @staticmethod
    def hessian(ϑ: np.ndarray, x: np.ndarray):
        a, b = ϑ

        if a < 0 or b < 0:
            return np.array([[nan] * 2] * 2)

        n = x.size

        return n * np.array(
            [
                [special.polygamma(1, a), -1 / b],
                [-1 / b, a / np.square(b)],
            ]
        )


def het_on_voxel(y, z, s):
    assert not np.any(s < 0), "Variance needs to be non-negative"

    # scale to avoid numerical issues

    norm = np.std(y)
    y_norm = y / norm
    s_norm = s / (norm * norm)

    # calculate beta

    neg_log_lik_fe = ReML.neg_log_lik(0, y_norm, z, s_norm)

    res = ReML.fit(y_norm, z, s_norm)
    neg_log_lik_me = res.fun

    var_res = 1 / ReML.hessian(res.x, y_norm, z, s_norm)
    beta = np.array([res.x, var_res])
    beta *= norm * norm

    # calculate lrt

    chisq = 2 * (neg_log_lik_fe - neg_log_lik_me)

    pseudor2 = 1 - neg_log_lik_me / neg_log_lik_fe
    pseudor2 = max(0, min(1, pseudor2))

    # calculate other

    i2 = MoM.i2(y_norm, z, s_norm)

    ϑ = InvGammaML.fit(s)
    var_ϑ = np.linalg.inv(InvGammaML.hessian(ϑ, s))
    gamma = np.vstack([ϑ, var_ϑ])

    n = s.size
    u = np.sum(1 / s)
    v = np.sum(1 / np.square(s))
    νq = (n - 1) * u / (np.square(u) - v)
    typical = float(νq)

    return dict(
        hetnorm=norm,
        hetbeta=beta,
        hetgamma=gamma,
        hettypical=typical,
        heti2=i2,
        hetpseudor2=pseudor2,
        hetchisq=chisq,
    )


class Heterogeneity(ModelAlgorithm):
    model_outputs: list[str] = [
        "hetnorm",
        "hetbeta",
        "hetgamma",
        "hettypical",
        "heti2",
        "hetpseudor2",
        "hetchisq",
    ]
    contrast_outputs: list[str] = []

    @staticmethod
    def voxel_calc(
        coordinate: tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: dict,
    ) -> dict | None:
        _ = cmatdict
        y, z, s = flame1_prepare_data(y, z, s)

        try:
            voxel_dict = het_on_voxel(y, z, s)
        except (np.linalg.LinAlgError, AssertionError, ValueError):
            return None
        except Exception as e:
            logger.warning(f"Unexpected exception for voxel {coordinate}", exc_info=e)
            return None

        if voxel_dict is None:
            return None

        voxel_result = {coordinate: voxel_dict}
        return voxel_result

    @classmethod
    def write_outputs(
        cls, ref_img: nib.Nifti1Image, cmatdict: dict, voxel_results: dict
    ) -> dict:
        output_files = dict()

        rdf = pd.DataFrame.from_records(voxel_results)

        for map_name, series in rdf.iterrows():
            assert isinstance(map_name, str)

            fname = cls.write_map(ref_img, map_name, series)
            output_files[map_name] = str(fname)

        return output_files
