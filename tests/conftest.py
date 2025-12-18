# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import tarfile
from typing import Any

import pytest

from halfpipe.logging import logger
from halfpipe.resource import get as get_resource

from .resource import setup as setup_test_resources

os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"


@pytest.fixture(scope="session", autouse=True)
def logging(request: pytest.FixtureRequest) -> None:
    logging_plugin = request.config.pluginmanager.get_plugin("logging-plugin")
    if logging_plugin is None:
        raise ValueError("Logging plugin not found")
    logger.setLevel("DEBUG")
    logger.addHandler(logging_plugin.log_cli_handler)


@pytest.fixture(scope="session")
def wakemandg_hensonrn_raw(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    tmp_path = tmp_path_factory.mktemp(basename="wakemandg_hensonrn")

    os.chdir(str(tmp_path))

    setup_test_resources()
    inputtarpath = get_resource("wakemandg_hensonrn_statmaps.tar.gz")

    with tarfile.open(inputtarpath) as fp:
        fp.extractall(tmp_path)

    subjects = [f"{i + 1:02d}" for i in range(16)]
    suffixes = ["stat-effect_statmap", "stat-variance_statmap", "mask"]

    data = {
        suffix: [
            tmp_path
            / (
                f"sub-{subject}_task-faces_feature-taskBased_"
                "taskcontrast-facesGtScrambled_model-aggregateTaskBasedAcrossRuns_"
                f"contrast-intercept_{suffix}.nii.gz"
            )
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
