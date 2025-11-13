# -*- coding: utf-8 -*-

from functools import partial
from pathlib import Path

from halfpipe.logging import logger

from .pilot_functions import (
    _set_work_dir,
    check_and_run_tab_refresh,
    settable_scroll_screen_down,
)
from .utils.compare_jsons import compare_json_files

widget_label_map = {
    "dualReg_1": "#feature_item_4_flabel",
    "corrMatrix_1": "#feature_item_1_flabel",
    "taskBased_1": "#feature_item_0_flabel",
    "fALFF_1": "#feature_item_2_flabel",
    "seedCorr_1": "#feature_item_3_flabel",
    "reHo_1": "#feature_item_5_flabel",
    "taskBased_2": "#feature_item_6_flabel",
    "fALFF_2": "#feature_item_7_flabel",
    "preproc_1": "#feature_item_8_flabel",
}
import pytest


async def run_before(
    pilot,
    data_path=None,
    spec_file_dir_path=None,
    covariant_spreadsheet_path=None,
    feature_label=None,
    scroll_to_remaining_part=False,
) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker
    feature_label = feature_label if feature_label is not None else None

    # pilot.app.reload_ui()
    if isinstance(data_path, Path):
        data_path = str(data_path)
    if isinstance(spec_file_dir_path, Path):
        work_dir_path = str(spec_file_dir_path)
        # work_dir_path = "/makethisfail/"
    if isinstance(covariant_spreadsheet_path, Path):
        covariant_spreadsheet_path = str(covariant_spreadsheet_path)

    logger.info(
        f"Setting data path: {data_path}, work dir path: {work_dir_path}, \
    covariant spreadsheet path: {covariant_spreadsheet_path}"
    )

    await _set_work_dir(pilot, work_dir_path, load_from_spec_file=True)

    # click Ok on Modal informing us that all data and workdir are set and user can proceed further
    # click Ok on Modal informing us that all data and workdir are set and user can proceed further
    try:
        await pilot.click("#only_one_button")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)

    # For some reason the button remains focussed when I do it locally, but it is not focussed when it runs through CI,
    # the tab should prevent this.
    if feature_label is None:
        await check_and_run_tab_refresh(pilot)
        await settable_scroll_screen_down(pilot, 50)
        # save
        await pilot.click("#save_button")
        await pilot.click("#only_one_button")
    else:
        # await sleep(10)
        await pilot.press("f")
        if scroll_to_remaining_part:
            # await pilot.click(offset=(15, feature_number))
            await pilot.click("#sidebar")
            for _i in range(30):
                await pilot.press("down")
        # await settable_scroll_screen_down(pilot, 28)
        # select particular feature tab
        # await pilot.click(offset=(15, feature_number))
        await pilot.click(widget_label_map[feature_label])
        # the features are not loaded in order as they appear on the screen
        # here is the order - features connection
        # feature_item_4_flabel: dualReg_1
        # feature_item_1_flabel: corrMatrix_1
        # feature_item_0_flabel: taskBased_1
        # feature_item_2_flabel: fALFF_1
        # feature_item_3_flabel: SeedCprr_1
        # feature_item_5_flabel: reHo_1
        # feature_item_6_flabel: taskBased_2
        # feature_item_7_flabel: fALFF_2
        # feature_item_8_flabel: preproc_1

        # await pilot.press('tab')
        # await pilot.press('enter')

        # await settable_scroll_screen_down(pilot, 50)
        # click on the form area
        await pilot.click(offset=(55, 10))
        # scroll
        await settable_scroll_screen_down(pilot, 20)


@pytest.mark.forked
def test_load_from_spec_file_f0(
    snap_compare,
    start_app,
    spec_file_dir_path: Path,
    downloaded_data_path: Path,
    atlases_maps_seed_images_path: Path,
    covariant_spreadsheet_path: Path,
    feature_label: str = "taskBased_1",
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
        feature_label=feature_label,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f1(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "taskBased_2"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f2(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "seedCorr_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f3(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "dualReg_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f4(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "corrMatrix_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f5(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "reHo_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f6(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "fALFF_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f7(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "fALFF_2"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f8(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "preproc_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_resave_spec_file(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, covariant_spreadsheet_path: Path
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
    )

    file1 = spec_file_dir_path / "spec.json"
    file2 = spec_file_dir_path / "spec_reference.json"

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
    assert compare_json_files(file1, file2)
