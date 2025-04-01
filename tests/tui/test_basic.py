# -*- coding: utf-8 -*-

import os
import shutil
from functools import partial
from pathlib import Path

from .pilot_functions import _load_data, _set_work_dir, set_non_bids_data, settable_scroll_screen_down


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
    # Delete work_dir if exists
    if os.path.exists(work_dir_path):
        shutil.rmtree(work_dir_path)

    if stage == "work_tab":
        await _set_work_dir(pilot, work_dir_path)
        # For some reason the button remains focussed when I do it locally, but it is not focussed when it runs through CI,
        # the tab should prevent this.
        await pilot.click(offset=(90, 30))

    if stage == "bids_data_tab":
        await _load_data(pilot, data_path)

    if stage == "non_bids_data_tab" or stage == "preproc_settings":
        await _set_work_dir(pilot, work_dir_path)

        if isinstance(t1_path_pattern, Path):
            t1_path_pattern = str(t1_path_pattern)
        if isinstance(bold_path_pattern, Path):
            bold_path_pattern = str(bold_path_pattern)
        await set_non_bids_data(pilot, t1_path_pattern, bold_path_pattern, set_repetition_time=stage == "preproc_settings")
        # same reason for this as at work_tab case
        await pilot.click(offset=(25, 25))
        await pilot.click(offset=(25, 25))
        if stage == "preproc_settings":
            # Select preprocessing settings tab
            await pilot.press("p")
            # Toggle run recon all
            # await pilot.click(offset=(109, 11))
            await pilot.click("#run_reconall")
            # Turn on slice timing
            # await pilot.click(offset=(113, 19))
            await pilot.click("#time_slicing_switch")

            # Check meta data modal. Click No to 'Proceed with these values?'
            # await pilot.click(offset=(116, 31))
            await pilot.click("#only_one_button")
            # Specify slice acquisition direction, choose second choice
            # await pilot.click(offset=(65, 26))
            await pilot.click("#set_value_modal")
            await pilot.press("down")
            await pilot.press("enter")
            # Click ok
            # await pilot.click(offset=(132, 30))
            # Click ok on the warning modal: Missing images
            await pilot.click(pilot.app.get_widget_by_id("only_one_button"))

            # await pilot.click(offset=(116, 31))
            # await pilot.click("#only_one_button")
            # Specify Slice timing modal: Choose third options
            # await pilot.click(offset=(65, 25))
            await pilot.click("#radio_set")
            for _i in range(2):
                await pilot.press("down")
            await pilot.press("enter")

            # Click ok on the 'Specify Slice timing modal'
            # await pilot.click(offset=(132, 34))
            await pilot.click("#ok")

            # click in the input box to set initial volumes to remove
            # await pilot.click(offset=(121, 31))
            await pilot.click("#number_of_remove_initial_volumes")
            # Type '9'
            await pilot.press("9")
            # random click to unfocus the input
            await pilot.click(offset=(50, 10))

            # Select Check and Run tab
            await pilot.press("r")
            # Click 'Refresh'
            # await pilot.click(offset=(85, 9))
            await pilot.click("#refresh_button")
            await settable_scroll_screen_down(pilot, 10)


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


def test_preproc_settings_tab(
    snap_compare, start_app, work_dir_path: Path, t1_path_pattern: Path, bold_path_pattern: Path
) -> None:
    """Starts as test_non_bids_data_input_tab but sets repetition time to some values and further checks general preprocessing
    settings, such as Run recon all, Turn on slice timing (which triggers a series of modals to check and set meta values
    and lastly set remove initial volumes to some particular number. At the end, the spec preview is checked."""
    run_before_with_extra_args = partial(
        run_before,
        work_dir_path=work_dir_path,
        t1_path_pattern=t1_path_pattern,
        bold_path_pattern=bold_path_pattern,
        stage="preproc_settings",
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
