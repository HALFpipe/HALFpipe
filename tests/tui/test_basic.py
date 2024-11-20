# -*- coding: utf-8 -*-

from functools import partial
from pathlib import Path

from .pilot_functions import _load_data, _set_work_dir, set_non_bids_data


async def run_before(
    pilot, data_path=None, work_dir_path=None, t1_path_pattern=None, bold_path_pattern=None, stage=None
) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker

    pilot.app.reload_ui()
    if isinstance(data_path, Path):
        data_path = str(data_path)
    if isinstance(work_dir_path, Path):
        work_dir_path = str(work_dir_path)
        # work_dir_path = "/makethisfail/"

    if stage == "work_tab":
        await _set_work_dir(pilot, work_dir_path)
        # For some reason the button remains focussed when I do it locally, but it is not focussed when it runs through CI,
        # the tab should prevent this.
        await pilot.click(offset=(90, 30))

    if stage == "bids_data_tab":
        await _load_data(pilot, data_path)

    if stage == "non_bids_data_tab":
        if isinstance(t1_path_pattern, Path):
            t1_path_pattern = str(t1_path_pattern)
        if isinstance(bold_path_pattern, Path):
            bold_path_pattern = str(bold_path_pattern)
        await set_non_bids_data(pilot, t1_path_pattern, bold_path_pattern)


def test_work_dir_tab(snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="work_tab"
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_bids_data_input_tab(snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path) -> None:
    """Check whether a bids data can be loaded. This should yield some non-zero found files at the file summary panel."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="bids_data_tab"
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_non_bids_data_input_tab(
    snap_compare, start_app, work_dir_path: Path, t1_path_pattern: Path, bold_path_pattern: Path
) -> None:
    """Check the non bids data input. In particular whether T1 and bold files can be loaded."""
    run_before_with_extra_args = partial(
        run_before,
        work_dir_path=work_dir_path,
        t1_path_pattern=t1_path_pattern,
        bold_path_pattern=bold_path_pattern,
        stage="non_bids_data_tab",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
