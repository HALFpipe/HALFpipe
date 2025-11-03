# -*- coding: utf-8 -*-

import os
import shutil
from functools import partial
from pathlib import Path

import pytest
from textual._wait import wait_for_idle

from halfpipe.logging import logger

from .pilot_functions import (
    _load_data,
    _select_covariates_spreadsheet,
    _select_group_level_models_cutoffs_values,
    _set_work_dir,
    add_new_feature,
    check_and_run_tab_refresh,
    select_images,
    settable_scroll_screen_down,
)


async def run_before(pilot, data_path=None, work_dir_path=None, covariant_spreadsheet_path=None, stage=None) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker
    # how_much_down = 0

    # pilot.app.reload_ui()
    if isinstance(data_path, Path):
        data_path = str(data_path)
    if isinstance(work_dir_path, Path):
        work_dir_path = str(work_dir_path)
    if isinstance(covariant_spreadsheet_path, Path):
        covariant_spreadsheet_path = str(covariant_spreadsheet_path)
    # Delete work_dir if exists
    if os.path.exists(work_dir_path):
        shutil.rmtree(work_dir_path)
    logger.info(
        f"Setting data path: {data_path}, work dir path: {work_dir_path}, \
    covariant spreadsheet path: {covariant_spreadsheet_path}"
    )

    # Define functions to execute based on stage requirements
    async def add_feature_related_tasks():
        await add_new_feature(pilot)
        await select_images(pilot)

    async def add_intercept_only_model():
        await add_new_feature(pilot, tab_type="g", feature_type="intercept_only", label="intercept_only_1")

    async def add_linear_model():
        await add_new_feature(pilot, tab_type="g", feature_type="linear_model", label="linear_model_1")

    async def select_aggregate():
        # await pilot.click(offset=(72, 15))
        await pilot.click("#aggregate_selection_list")
        await pilot.press("down")
        await pilot.press("enter")

    async def toggle_cutoff_panel():
        # toggle on/off switch
        # await pilot.click(offset=(138, 21))
        await pilot.click(pilot.app.get_widget_by_id("cutoff_panel").get_widget_by_id("exclude_subjects"))
        # await pilot.click('#cutoff_panel_switch')

    async def select_group_level_models_cutoffs_values():
        await _select_group_level_models_cutoffs_values(pilot)

    async def select_covariates_spreadsheet():
        await _select_covariates_spreadsheet(pilot, covariant_spreadsheet_path)
        # scroll to see more
        # await settable_scroll_screen_down(pilot, 29)

    async def duplicate():
        # await pilot.click(offset=(10, 12))
        # click on the form area
        # await pilot.click(offset=(55, 10))
        # await pilot.click("#duplicate_item_button")
        await pilot.click(pilot.app.get_widget_by_id("models_content").get_widget_by_id("duplicate_item_button"))
        # confirm new name
        await pilot.click("#ok")

        # scroll to see more
        await settable_scroll_screen_down(pilot, 29)

    async def final_stage_tasks():
        # press check and run also manually
        # await pilot.click(offset=(108, 4))
        await check_and_run_tab_refresh(pilot)
        await settable_scroll_screen_down(pilot, 60)
        # os.rename(Path(work_dir_path) / "spec.json", Path(work_dir_path) / f"spec_{stage}.json")

    # Map stages to the tasks they should trigger
    tasks_by_stage = {
        "intercept_only_at_group_level_models_tab": [
            add_feature_related_tasks,
            add_intercept_only_model,
            select_aggregate,
            toggle_cutoff_panel,
        ],
        "intercept_only_at_spec_preview": [
            add_feature_related_tasks,
            add_intercept_only_model,
            select_aggregate,
            toggle_cutoff_panel,
            final_stage_tasks,
        ],
        "intercept_only_at_group_level_models_tab_duplicate": [
            add_feature_related_tasks,
            add_intercept_only_model,
            select_aggregate,
            toggle_cutoff_panel,
            duplicate,
        ],
        "linear_model_at_group_level_models_tab": [add_feature_related_tasks, add_linear_model, select_covariates_spreadsheet],
        "linear_model_at_group_level_models_tab_duplicate": [
            add_feature_related_tasks,
            add_linear_model,
            select_covariates_spreadsheet,
            duplicate,
        ],
        "linear_model_at_spec_preview": [
            add_feature_related_tasks,
            add_linear_model,
            select_covariates_spreadsheet,
            final_stage_tasks,
        ],
    }
    # if stage == "at_spec_preview":
    #     how_much_down = 60
    # elif stage == "duplicate_at_spec_preview":
    #     how_much_down = 36

    # Execute tasks based on the specified stage
    # set work dir
    await _set_work_dir(pilot, work_dir_path)
    # set data dir
    await _load_data(pilot, data_path)
    # # click Ok on Modal informing us that all data and workdir are set and user can proceed further
    await pilot.click("#only_one_button")
    for task in tasks_by_stage[stage]:
        await task()


@pytest.mark.forked
def test_intercept_only_at_global_models_tab(snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path) -> None:
    """Add Task-based feature, add intercept only group level model, make cutoff choices"""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        stage="intercept_only_at_group_level_models_tab",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_intercept_only_at_group_level_models_tab_duplicate(
    snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path
) -> None:
    """Add Task-based feature, add intercept only group level model, make cutoff choices, then duplicate"""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        stage="intercept_only_at_group_level_models_tab_duplicate",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_intercept_only_at_spec_preview(snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path) -> None:
    """Add Task-based feature, add intercept only group level model, make cutoff choices, check spec file preview"""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="intercept_only_at_spec_preview"
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_linear_model_at_group_level_models_tab(
    snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path, covariant_spreadsheet_path: Path
) -> None:
    """Add Task-based feature, add linear group level model, add spreadsheet"""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
        stage="linear_model_at_group_level_models_tab",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_linear_model_at_group_level_models_tab_duplicate(
    snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path, covariant_spreadsheet_path: Path
) -> None:
    """Add Task-based feature, add linear group level model, add spreadsheet and duplicate"""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
        stage="linear_model_at_group_level_models_tab_duplicate",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_linear_model_at_spec_preview(
    snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path, covariant_spreadsheet_path: Path
) -> None:
    """Add Task-based feature, add linear group level model, add spreadsheet and check spec preview"""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
        stage="linear_model_at_spec_preview",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
