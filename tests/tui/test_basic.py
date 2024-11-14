# -*- coding: utf-8 -*-

from functools import partial
from pathlib import Path

from .pilot_functions import (
    _load_data,
    _set_work_dir,
)


async def run_before(pilot, data_path=None, work_dir_path=None, stage=None) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker

    pilot.app.reload_ui()
    if isinstance(data_path, Path):
        data_path = str(data_path)
    if isinstance(work_dir_path, Path):
        #  work_dir_path = str(work_dir_path)
        work_dir_path = "/makethisfail"

    if stage == "work_tab":
        await _set_work_dir(pilot, work_dir_path)

    if stage == "bids_data_tab":
        await _load_data(pilot, data_path)


# circumvent downloading the data since this will come later when the test itself is ok
# def test_task_based_features(
#     snap_compare, start_app, fixed_tmp_path: Path, work_dir_path: Path, downloaded_data_path: Path
# ) -> None:

# circumvent downloading the data since this will come later when the test itself is ok
# downloaded_data_path = "/home/tomas/github/HALFpipe/tests/workflows/bla"


def test_work_dir_tab(snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path) -> None:
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="work_tab"
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_bids_data_input_tab(snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path) -> None:
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="bids_data_tab"
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
