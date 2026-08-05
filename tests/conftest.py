# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import shutil
import tarfile
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from halfpipe import resource
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

    data: dict[str, Any] = {
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


@pytest.fixture(scope="session")
def atlases_maps_seed_images_path() -> Path:
    path = Path("/tmp/atlases_and_maps/")
    path.mkdir(parents=True, exist_ok=True)  # Ensure the path exists

    setup_test_resources()

    for item in [
        "FIND_ica_maps_2009.nii.gz",
        "tpl-MNI152NLin2009cAsym_atlas-schaefer2011Combined_dseg.nii",
        "tpl-MNI152NLin2009cAsym_atlas-brainnetomeCombined_dseg.nii",
        "R_vmPFC_seed_2009.nii.gz",
        "R_vlPFC_pt_seed_2009.nii.gz",
        "R_vlPFC_po_seed_2009.nii.gz",
    ]:
        target_path = path / item
        if not target_path.is_file():
            target_path.symlink_to(resource.get(item))

    atlases_path = get_resource("atlases.zip")
    with ZipFile(atlases_path) as zip_file:
        zip_file.extractall(path)

    return path


@pytest.fixture(scope="session", autouse=True)
def resolved_test_dir_path():
    """Fixture to resolve paths and handle fallback to './' if necessary."""
    source_file = Path("/home/runner/actions-runner/_work/HALFpipe/HALFpipe/tests/tui")
    if not source_file.exists():  # Fallback to './' if not found in CURRENT_DIR
        source_file = Path("../tui/")
    logger.info(f"Main test directory path is {Path.cwd()}")
    return source_file


@pytest.fixture(scope="session")
def covariant_spreadsheet_path(fixed_tmp_path, resolved_test_dir_path) -> Path:
    source_file = resolved_test_dir_path / "Covariates.xlsx"
    destination_file = fixed_tmp_path / "Covariates.xlsx"
    if os.path.exists(destination_file):
        os.remove(destination_file)
    shutil.copy(source_file, destination_file)
    return destination_file
