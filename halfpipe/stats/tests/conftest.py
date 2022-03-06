# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import tarfile
from pathlib import Path

import pytest
from nipype.interfaces import ants
from templateflow.api import get as get_template

from ...resource import get as getresource
from ...tests.resource import setup as setuptestresources


@pytest.fixture(scope="package")
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
            tmp_path
            / f"sub-{subject}_task-faces_feature-taskBased_taskcontrast-facesGtScrambled_model-aggregateTaskBasedAcrossRuns_contrast-intercept_{suffix}.nii.gz"
            for subject in subjects
        ]
        for suffix in suffixes
    }

    data.update(
        {
            "subjects": subjects,
            "spreadsheet": tmp_path / "subjects_age_sex.csv",
        }
    )

    return data


@pytest.fixture(scope="package")
def mni_downsampled(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="mni_downsampled")

    os.chdir(str(tmp_path))

    tpl = get_template("MNI152NLin2009cAsym", resolution=2, desc="brain", suffix="mask")

    result = ants.ResampleImageBySpacing(
        dimension=3, input_image=tpl, out_spacing=(6, 6, 6)
    ).run()
    assert result.outputs is not None

    return result.outputs.output_image


@pytest.fixture(scope="package")
def wakemandg_hensonrn_downsampled(
    tmp_path_factory, wakemandg_hensonrn, mni_downsampled
):
    tmp_path = tmp_path_factory.mktemp(basename="wakemandg_hensonrn_downsampled")

    os.chdir(str(tmp_path))

    data = dict()

    def _downsample(in_file):
        result = ants.ApplyTransforms(
            dimension=3,
            input_image_type=0,
            input_image=in_file,
            reference_image=mni_downsampled,
            interpolation="NearestNeighbor",
            transforms=["identity"],
        ).run()
        assert result.outputs is not None

        return result.outputs.output_image

    for k, v in wakemandg_hensonrn.items():
        if isinstance(v, list):
            data[k] = [_downsample(f) if Path(f).exists() else f for f in v]
        else:
            data[k] = v

    return data
