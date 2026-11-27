# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
import pytest

from halfpipe.stats.heterogeneity import het_on_voxel, reml_neg_log_lik, reml_terms


def test_reml_terms_inverse_variance() -> None:
    x = np.ones((4, 1), dtype=np.float64)
    s = np.array([[0.2], [0.5], [1.0], [2.0]], dtype=np.float64)
    theta = 0.5

    terms = reml_terms(theta, x, s)
    expected_inv_var = 1.0 / (s + theta).ravel()

    assert np.allclose(terms.inverse_variance, expected_inv_var)
    assert np.allclose(terms.gram_matrix, np.array([[expected_inv_var.sum()]]))


def test_reml_neg_log_lik_zero_tau_allowed_with_positive_variance() -> None:
    y = np.array([[1.2], [2.5], [0.4], [3.1], [1.8]], dtype=np.float64)
    x = np.ones((5, 1), dtype=np.float64)
    s = np.array([[0.2], [0.5], [0.3], [0.4], [0.25]], dtype=np.float64)

    assert np.isfinite(reml_neg_log_lik(0.0, y, x, s))
    assert np.isinf(reml_neg_log_lik(-0.1, y, x, s))
    assert np.isinf(reml_neg_log_lik(0.0, y, x, np.zeros_like(s)))


@pytest.mark.parametrize(
    ("design", "expected_tau2", "expected_chisq"),
    [
        # Reference values verified with R metafor::rma(..., method="REML")
        (np.ones((10, 1), dtype=np.float64), 0.7725403, 12.82993),
        (
            np.column_stack(
                [
                    np.ones(10, dtype=np.float64),
                    np.array([-1.5, -1.0, -0.5, 0.0, 0.2, 0.5, 0.8, 1.0, 1.2, 1.5]),
                ]
            ),
            0.7892084,
            12.23507,
        ),
    ],
)
def test_het_on_voxel_matches_reml_reference(
    design: np.ndarray,
    expected_tau2: float,
    expected_chisq: float,
) -> None:
    y = np.array([[1.2, 2.5, 0.4, 3.1, 1.8, 2.9, 0.7, 2.2, 1.5, 3.4]], dtype=np.float64).T
    s = np.array([[0.2, 0.5, 0.3, 0.4, 0.25, 0.6, 0.15, 0.35, 0.45, 0.3]], dtype=np.float64).T

    result = het_on_voxel(y, design, s)

    assert np.isclose(result["hetbeta"][0], expected_tau2, rtol=1e-4)
    assert np.isfinite(result["hetchisq"])
    assert np.isclose(result["hetchisq"], expected_chisq, rtol=1e-4)
    assert 0.0 < result["hetpseudor2"] < 1.0


def test_het_on_voxel_equal_variances_exact_reml() -> None:
    rng = np.random.default_rng(42)
    s0 = 0.5
    n = 50
    y = rng.normal(loc=2.0, scale=np.sqrt(s0 + 1.5), size=(n, 1))
    s = np.full((n, 1), s0, dtype=np.float64)
    z = np.ones((n, 1), dtype=np.float64)

    expected_tau2 = max(0.0, float(np.var(y, ddof=1) - s0))
    result = het_on_voxel(y, z, s)

    assert np.isclose(result["hetbeta"][0], expected_tau2, rtol=1e-4)
    assert np.isfinite(result["hetchisq"])
    assert result["hetchisq"] > 0.0
