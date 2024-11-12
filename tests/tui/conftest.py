# -*- coding: utf-8 -*-
# conftest.py
from pathlib import Path

import pytest

from halfpipe.tui.base import MainApp  # Ensure path aligns with your project structure

from ..workflows.datasets import Dataset  # Adjust this import path as needed


# Custom fixture that returns a specific path, this is needed so that the path in the snapshot is always the same
# If the path was variable then the snapshot would yield failure.
@pytest.fixture(scope="module")
def fixed_tmp_path() -> Path:
    path = Path("/tmp/tui_test/")
    path.mkdir(parents=True, exist_ok=True)  # Ensure the path exists
    return path
    # Clean up after the test, is this needed?
    # shutil.rmtree(path)


# Define the fixture with module scope, one subject, three tasks
@pytest.fixture(scope="module")
def downloaded_data_path(fixed_tmp_path) -> Path:
    dataset = Dataset(
        name="PIOP1",
        openneuro_id="ds002785",
        openneuro_url="https://openneuro.org/datasets/ds002785/versions/2.0.0",
        url="https://github.com/OpenNeuroDatasets/ds002785.git",
        paths=[
            "sub-0001/anat",
            "sub-0001/func/sub-0001_task-anticipation_acq*",
            "sub-0001/func/sub-0001_task-workingmemory_acq*",
            "sub-0001/func/sub-0001_task-restingstate_acq*",
        ],
    )

    data_path = fixed_tmp_path / "ds002785/"
    dataset.download(data_path)
    return data_path


@pytest.fixture(scope="module")
def work_dir_path(fixed_tmp_path) -> Path:
    return fixed_tmp_path / "work_dir/"


# should yield a fresh instance each time, but apparently it does not
@pytest.fixture(scope="function")
def start_app():
    return MainApp()
