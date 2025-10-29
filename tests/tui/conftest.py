# -*- coding: utf-8 -*-
# conftest.py
import os
import shutil
import sys
from pathlib import Path

import pytest

from halfpipe.logging import logger
from halfpipe.tui.base import MainApp  # Ensure path aligns with your project structure

from ..create_mock_bids_dataset import create_bids_data


@pytest.fixture(scope="session", autouse=True)
def resolved_test_dir_path():
    """Fixture to resolve paths and handle fallback to './' if necessary."""
    source_file = Path("/home/runner/actions-runner/_work/HALFpipe/HALFpipe/tests/tui/")
    if not source_file.exists():  # Fallback to './' if not found in CURRENT_DIR
        source_file = Path("./")
    logger.info(f"TUI test directory path is {Path.cwd()}")
    return source_file


@pytest.fixture(scope="session", autouse=True)
def copy_jinja2_file(resolved_test_dir_path):
    """Copy a file before tests start. This is just a hot fix because somehow the resources directory
    is delete during the docker build."""
    source_file = resolved_test_dir_path / "snapshot_report_template.jinja2"

    # Dynamically get Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    destination = Path(f"/opt/conda/envs/fmriprep/lib/python{python_version}/site-packages/resources/")

    try:
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy(source_file, destination / "snapshot_report_template.jinja2")
    except Exception as e:
        logger.info(f"[WARN] snapshot_report_template.jinja2 cannot be copied. Exception: {e}")


# Custom fixture that returns a specific path, this is needed so that the path in the snapshot is always the same
# If the path was variable then the snapshot would yield failure.
@pytest.fixture(scope="session")
def fixed_tmp_path() -> Path:
    path = Path("/tmp/tui_test/")
    path.mkdir(parents=True, exist_ok=True)  # Ensure the path exists
    return path


# Define the fixture with module scope, one subject, three tasks
@pytest.fixture(scope="session")
def downloaded_data_path(fixed_tmp_path) -> Path:
    tasks_conditions_dict = {
        "anticipation_acq-seq": ["cue_negative", "cue_neutral", "img_negative", "img_neutral"],
        "workingmemory_acq-seq": ["active_change", "active_nochange", "passive"],
        "restingstate_acq-mb3": [],
    }
    data_path = fixed_tmp_path / "ds002785"
    create_bids_data(data_path, number_of_subjects=1, tasks_conditions_dict=tasks_conditions_dict, field_maps=True)
    return data_path


@pytest.fixture(scope="session")
def work_dir_path(fixed_tmp_path) -> Path:
    return fixed_tmp_path / "work_dir/"


@pytest.fixture(scope="session")
def spec_file_dir_path(fixed_tmp_path, resolved_test_dir_path) -> Path:
    source_dir = resolved_test_dir_path / "spec_file_for_load_test"
    destination_dir = fixed_tmp_path / "spec_file_for_load_test/"
    if os.path.exists(destination_dir):
        shutil.rmtree(destination_dir)
    shutil.copytree(source_dir, destination_dir)
    return destination_dir


@pytest.fixture(scope="session")
def covariant_spreadsheet_path(fixed_tmp_path, resolved_test_dir_path) -> Path:
    source_file = resolved_test_dir_path / "Covariates.xlsx"
    destination_file = fixed_tmp_path / "Covariates.xlsx"
    if os.path.exists(destination_file):
        os.remove(destination_file)
    shutil.copy(source_file, destination_file)
    return destination_file


@pytest.fixture(scope="session")
def t1_path_pattern(downloaded_data_path) -> Path:
    return downloaded_data_path / "sub-{subject}/anat/sub-{subject}_T1w.nii.gz"


@pytest.fixture(scope="session")
def bold_path_pattern(downloaded_data_path) -> Path:
    return downloaded_data_path / "sub-{subject}/func/sub-{subject}_task-{task}_bold.nii.gz"


@pytest.fixture(scope="session")
def event_path_pattern(downloaded_data_path) -> Path:
    return downloaded_data_path / "sub-{subject}/func/sub-{subject}_task-{task}_events.tsv"


@pytest.fixture(scope="session")
def magnitude_fmap_pattern(downloaded_data_path) -> Path:
    return downloaded_data_path / "sub-{subject}/fmap/sub-{subject}_magnitude1.nii.gz"


@pytest.fixture(scope="session")
def phase_diff_fmap_pattern(downloaded_data_path) -> Path:
    return downloaded_data_path / "sub-{subject}/fmap/sub-{subject}_phasediff.nii.gz"


@pytest.fixture(scope="function")
def start_app():
    from types import SimpleNamespace

    opts = SimpleNamespace()
    opts.fs_root = "/"
    app = MainApp(opts)
    return app
