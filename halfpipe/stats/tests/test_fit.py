# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import pytest

import os

from ..fit import fit
from ..design import group_design


@pytest.mark.slow
@pytest.mark.timeout(600)
def test_fit(tmp_path, wakemandg_hensonrn_downsampled):
    os.chdir(str(tmp_path))

    # prepare
    data = wakemandg_hensonrn_downsampled

    cope_files = data["stat-effect_statmap"]
    var_cope_files = data["stat-variance_statmap"]
    mask_files = data["mask"]

    subjects = data["subjects"]
    spreadsheet_file = data["spreadsheet"]

    regressors, contrasts, _, _ = group_design(
        subjects=subjects,
        spreadsheet=spreadsheet_file,
        variabledicts=[
            {"name": "Sub", "type": "id"},
            {"name": "Age", "type": "continuous"},
            {"name": "ReactionTime", "type": "categorical"},
        ],
        contrastdicts=[
            {"variable": ["Age"], "type": "infer"},
            {"variable": ["ReactionTime"], "type": "infer"},
        ],
    )

    result = fit(
        cope_files=cope_files,
        var_cope_files=var_cope_files,
        mask_files=mask_files,
        regressors=regressors,
        contrasts=contrasts,
        algorithms_to_run=["mcartest", "heterogeneity"],
        num_threads=1,
    )

    assert len(result) > 0
    assert "hetchisq" in result
    assert "mcarz" in result
