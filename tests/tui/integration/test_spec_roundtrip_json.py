
from pathlib import Path

import pytest

from halfpipe.logging import logger
from tests.tui.spec_file_load_flow import run_before

from compare_jsons import compare_json_files
from textual import pilot


def test_load_from_spec_file_resave_spec_file(
    start_app, spec_file_dir_path: Path, downloaded_data_path: Path, covariant_spreadsheet_path: Path
) -> None:

    run_before(
        pilot,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
        feature_label=None,
        scroll_to_remaining_part=False,
    )

    file1 = spec_file_dir_path / "spec.json"
    file2 = spec_file_dir_path / "spec_reference.json"

    assert compare_json_files(file1, file2)
