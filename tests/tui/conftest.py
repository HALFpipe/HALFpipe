# -*- coding: utf-8 -*-
import shutil
from pathlib import Path

import pytest

from halfpipe.logging import logger
from halfpipe.tui.base import MainApp  # Ensure path aligns with your project structure

from ..create_mock_bids_dataset import create_bids_data


def pytest_collection_modifyitems(config, items):
    # Detect snapshot update mode
    snapshot_update = config.getoption("--snapshot-update", default=False) or config.getoption(
        "--snapshot-update", default=None
    )

    if not snapshot_update:
        return

    for item in items:
        # Remove forked marker during snapshot update
        item.own_markers = [m for m in item.own_markers if m.name != "forked"]


@pytest.fixture(scope="session", autouse=True)
def copy_jinja2_file() -> None:
    """Copy a file before tests start. This is just a hot fix because somehow the resources directory
    is delete during the docker build."""
    source_file = Path(__file__).parent / "snapshot_report_template.jinja2"

    import pytest_textual_snapshot

    # Path to the module file
    module_path = Path(pytest_textual_snapshot.__file__)

    # Go up one level (site-packages) and append "resources"
    destination = module_path.parent / "resources"

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
def downloaded_data_path(fixed_tmp_path: Path) -> Path:
    tasks_conditions_dict = {
        "anticipation_acq-seq": ["cue_negative", "cue_neutral", "img_negative", "img_neutral"],
        "workingmemory_acq-seq": ["active_change", "active_nochange", "passive"],
        "restingstate_acq-mb3": [],
    }
    data_path = fixed_tmp_path / "ds002785"
    create_bids_data(data_path, number_of_subjects=1, tasks_conditions_dict=tasks_conditions_dict, field_maps=True)
    return data_path


# @pytest.fixture(scope="session")
# def work_dir_path(fixed_tmp_path) -> Path:
#     return fixed_tmp_path / "work_dir/"
# import hashlib
#
# @pytest.fixture
# def work_dir_path(fixed_tmp_path, request) -> Path:
#     test_id = request.node.nodeid
#     suffix = hashlib.sha1(test_id.encode()).hexdigest()[:8]
#     return fixed_tmp_path / f"work_dir_{suffix}"


@pytest.fixture
def work_dir_path(fixed_tmp_path, request):
    name = request.node.name
    return fixed_tmp_path / f"work_dir_{name}"


@pytest.fixture(scope="session")
def spec_file_dir_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source_dir = Path(__file__).parent / "spec_file_for_load_test/"
    destination_dir = tmp_path_factory.mktemp("spec")
    shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)
    return destination_dir


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


#
# @pytest.fixture(scope="function")
# def start_app():
#     from types import SimpleNamespace
#
#     opts = SimpleNamespace()
#     opts.fs_root = "/"
#     app = MainApp(opts)
#     return app


@pytest.fixture
def start_app():
    from types import SimpleNamespace

    def make_app():
        opts = SimpleNamespace()
        opts.fs_root = "/"
        return MainApp(opts)

    return make_app
