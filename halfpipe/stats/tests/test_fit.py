# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os

import pytest

from ..fit import fit


@pytest.mark.slow
@pytest.mark.timeout(1200)
def test_fit(tmp_path, wakemandg_hensonrn):
    os.chdir(str(tmp_path))

    cope_files, var_cope_files, mask_files, regressors, contrasts = wakemandg_hensonrn

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
