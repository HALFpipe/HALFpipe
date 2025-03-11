# -*- coding: utf-8 -*-

from asyncio import sleep
from functools import partial
from pathlib import Path

from .pilot_functions import (
    _set_work_dir,
    check_and_run_tab_refresh,
    settable_scroll_screen_down,
)


async def run_before(
    pilot, data_path=None, spec_file_dir_path=None, feature_number=None, scroll_to_remaining_part=False
) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker
    feature_number = feature_number if feature_number is not None else None

    pilot.app.reload_ui()
    if isinstance(spec_file_dir_path, Path):
        work_dir_path = str(spec_file_dir_path)
        # work_dir_path = "/makethisfail/"

    await _set_work_dir(pilot, work_dir_path, load_from_spec_file=True)
    # For some reason the button remains focussed when I do it locally, but it is not focussed when it runs through CI,
    # the tab should prevent this.
    if feature_number is None:
        await check_and_run_tab_refresh(pilot)
        await settable_scroll_screen_down(pilot, 50)
    else:
        await sleep(10)
        await pilot.press("f")
        if scroll_to_remaining_part:
            await pilot.click(offset=(15, feature_number))
            await settable_scroll_screen_down(pilot, 28)
        # select particular feature tab
        await pilot.click(offset=(15, feature_number))
        # await settable_scroll_screen_down(pilot, 50)
        # click on the form area
        await pilot.click(offset=(55, 10))
        # scroll
        await settable_scroll_screen_down(pilot, 15)


def test_load_from_spec_file_f0(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 20) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number)

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f1(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 24) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number)

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f2(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 32) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number)

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f3(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 40) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number)

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f4(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 48) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number)

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f5(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 28) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number, scroll_to_remaining_part=True
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f6(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 36) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number, scroll_to_remaining_part=True
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f7(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 40) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number, scroll_to_remaining_part=True
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_load_from_spec_file_f8(snap_compare, start_app, spec_file_dir_path: Path, feature_number: int = 48) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, spec_file_dir_path=spec_file_dir_path, feature_number=feature_number, scroll_to_remaining_part=True
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


# Function to compare files since the 10th line
def compare_files(file1, file2):
    with open(file1, "r") as f1, open(file2, "r") as f2:
        # Skip the first 4 lines in both files
        f1_lines = f1.readlines()[4:-2]
        f2_lines = f2.readlines()[4:-2]
        # Return True if the remaining lines are the same, else False
        return f1_lines == f2_lines


def test_load_from_spec_file_resave_spec_file(snap_compare, start_app, spec_file_dir_path: Path) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(run_before, spec_file_dir_path=spec_file_dir_path)

    file1 = spec_file_dir_path / "spec.json"
    file2 = spec_file_dir_path / "spec_reference.json"

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
    assert compare_files(file1, file2) == True
