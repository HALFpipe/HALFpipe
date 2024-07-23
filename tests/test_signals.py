# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import nibabel as nib
import numpy as np
import pytest
from halfpipe.resource import get as get_resource
from halfpipe.signals import mean_signals, mode_signals
from halfpipe.stats.fit import load_data
from halfpipe.utils.matrix import atleast_4d
from nilearn.image import new_img_like

from .resource import setup as setup_test_resources


def test_mean_signals(tmp_path: Path, wakemandg_hensonrn_raw: dict[str, list[Any]]) -> None:
    os.chdir(str(tmp_path))

    cope_files = wakemandg_hensonrn_raw["stat-effect_statmap"]
    cope_image = nib.nifti1.load(cope_files[0])
    assert isinstance(cope_image, nib.analyze.AnalyzeImage)

    mask_files = wakemandg_hensonrn_raw["mask"]
    mask_image = nib.nifti1.load(mask_files[0])
    assert isinstance(mask_image, nib.analyze.AnalyzeImage)

    setup_test_resources()
    atlases_path = get_resource("atlases.zip")
    with ZipFile(atlases_path) as zip_file:
        zip_file.extractall(tmp_path)

    brainnetome_path = tmp_path / "atlas-Brainnetome_dseg.nii.gz"
    brainnetome_image = nib.nifti1.load(brainnetome_path)
    assert isinstance(brainnetome_image, nib.analyze.AnalyzeImage)

    brainnetome_signals, coverages = mean_signals(cope_image, brainnetome_image, mask_image=mask_image, output_coverage=True)
    assert np.all(np.isfinite(brainnetome_signals))
    assert np.all(np.isfinite(coverages))
    assert all(0 <= coverage <= 1 for coverage in coverages)

    schaefer_path = tmp_path / "atlas-Schaefer2018Combined_dseg.nii.gz"
    schaefer_image = nib.nifti1.load(schaefer_path)
    assert isinstance(schaefer_image, nib.analyze.AnalyzeImage)

    brainnetome = atleast_4d(np.asanyarray(brainnetome_image.dataobj).astype(np.int32))
    brainnetome_count = brainnetome.max()
    schaefer = atleast_4d(np.asanyarray(schaefer_image.dataobj).astype(np.int32))
    schaefer[schaefer > 0] += brainnetome_count

    combined = np.concatenate((brainnetome, schaefer), axis=3)
    combined_image = new_img_like(brainnetome_image, combined)

    combined_signals, coverages = mean_signals(cope_image, combined_image, mask_image=mask_image, output_coverage=True)
    assert np.all(np.isfinite(combined_signals))
    assert np.all(np.isfinite(coverages))
    assert all(0 <= coverage <= 1 for coverage in coverages)

    assert np.allclose(combined_signals[:, :brainnetome_count], brainnetome_signals)


@pytest.mark.timeout(600)
def test_mode_signals(tmp_path: Path, wakemandg_hensonrn_raw: dict[str, list[Any]]) -> None:
    os.chdir(str(tmp_path))

    cope_files = wakemandg_hensonrn_raw["stat-effect_statmap"]
    var_cope_files = wakemandg_hensonrn_raw["stat-variance_statmap"]
    mask_files = wakemandg_hensonrn_raw["mask"]

    copes_img, var_copes_img = load_data(cope_files, var_cope_files, mask_files)

    setup_test_resources()
    modes_path = get_resource("tpl-MNI152NLin2009cAsym_res-02_atlas-DiFuMo_desc-1024dimensions_probseg.nii.gz")
    modes_img = nib.nifti1.load(modes_path)
    assert isinstance(modes_img, nib.analyze.AnalyzeImage)

    signals = mode_signals(copes_img, var_copes_img, modes_img)

    assert np.all(np.isfinite(signals))
