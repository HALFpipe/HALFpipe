# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import shutil
import tarfile
from pathlib import Path
from typing import Any

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


@pytest.fixture(scope="session")
def atlases_maps_seed_images_path(fixed_tmp_path) -> Path:
    # set atlases, seed maps and spatial maps
    test_online_resources = {
        "FIND_ica_maps_2009.nii.gz": "https://drive.google.com/file/d/1XnFGm9aCcTIuXgKZ71fDqATBJWAxkInO/view?usp=drive_link",
        "tpl-MNI152NLin2009cAsym_atlas-schaefer2011Combined_dseg.nii": "https://drive.google.com/file/d/1CR0rjbznad-tkfVc1vrGKsKJg5_nrf5E/view?usp=drive_link",
        "tpl-MNI152NLin2009cAsym_atlas-brainnetomeCombined_dseg.nii": "https://drive.google.com/file/d/1MYF4VaZrWmQXL1Jl3ZWMg1tWaKBfPo4W/view?usp=drive_link",
        "R_vmPFC_seed_2009.nii.gz": "https://drive.google.com/file/d/16L_HXOrrMqw08BdGTOh7RTErNTVytyvS/view?usp=drive_link",
        "R_vlPFC_pt_seed_2009.nii.gz": "https://drive.google.com/file/d/1fNr8ctHpTN8XJn95mclMxTetKdpbdddV/view?usp=drive_link",
        "R_vlPFC_po_seed_2009.nii.gz": "https://drive.google.com/file/d/1te1g3tpFaHdjx8GyZ1myMg_ayaHXPYKO/view?usp=drive_link",
    }

    resource.resource_dir = Path(fixed_tmp_path / "atlases_maps_seed_images")
    resource.resource_dir.mkdir(exist_ok=True, parents=True)
    resource.online_resources.update(test_online_resources)

    for item in test_online_resources:
        resource.get(item)

    return resource.resource_dir


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
