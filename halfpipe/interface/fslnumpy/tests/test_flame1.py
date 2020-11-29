# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import pytest

import os
import tarfile
from pathlib import Path

import nibabel as nib
import numpy as np

from ....tests.resource import setup as setuptestresources
from ....resource import get as getresource

from ..flame1 import FLAME1
from nipype.interfaces import fsl

from ...imagemaths.merge import _merge, _merge_mask
from ...stats.model import _group_model


@pytest.fixture(scope="module")
def wakemandg_hensonrn(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="wakemandg_hensonrn")

    os.chdir(str(tmp_path))

    setuptestresources()
    inputtarpath = getresource("wakemandg_hensonrn_statmaps.tar.gz")

    with tarfile.open(inputtarpath) as fp:
        fp.extractall(tmp_path)

    subjects = [f"{i+1:02d}" for i in range(16)]
    suffixes = ["stat-effect_statmap", "stat-variance_statmap", "mask"]

    data = {
        suffix: [
            tmp_path / f"sub-{subject}_task-faces_feature-taskBased_taskcontrast-facesGtScrambled_model-aggregateTaskBasedAcrossRuns_contrast-intercept_{suffix}.nii.gz"
            for subject in subjects
        ]
        for suffix in suffixes
    }

    data.update({
        "subjects": subjects,
        "spreadsheet": tmp_path / "subjects_age_sex.csv",
    })

    return data


# @pytest.mark.timeout(3600)
def test_FLAME1(tmp_path, wakemandg_hensonrn):
    os.chdir(str(tmp_path))

    cope_files = wakemandg_hensonrn["stat-effect_statmap"]
    var_cope_files = wakemandg_hensonrn["stat-variance_statmap"]
    mask_files = wakemandg_hensonrn["mask"]

    subjects = wakemandg_hensonrn["subjects"]
    spreadsheet_file = wakemandg_hensonrn["spreadsheet"]

    regressors, contrasts, _ = _group_model(
        subjects=subjects,
        spreadsheet=spreadsheet_file,
        variabledicts=[
            {"name": "Sub", "type": "id"},
            {"name": "Age", "type": "continuous"},
            {"name": "ReactionTime", "type": "categorical"},
        ],
        contrastdicts=[
            {"variable": ["Age"], "type": "infer"},
            {"variable": ["ReactionTime"], "type": "infer"}
        ]
    )

    instance = FLAME1()

    instance.inputs.cope_files = cope_files
    instance.inputs.var_cope_files = var_cope_files
    instance.inputs.mask_files = mask_files

    instance.inputs.regressors = regressors
    instance.inputs.contrasts = contrasts

    result = instance.run()
