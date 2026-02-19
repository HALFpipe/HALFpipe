# -*- coding: utf-8 -*-

import os
import shutil
from functools import partial
from pathlib import Path

import pytest

from halfpipe.logging import logger

from ..pilot_functions import (
    _load_data,
    _set_work_dir,
    add_atlas_or_seed_or_map_file_pattern,
    add_new_feature,
    check_and_run_tab_refresh,
    click_until_gone,
    select_file_tags,
    select_images,
    settable_scroll_screen_down,
)


async def run_before(pilot, data_path=None, work_dir_path=None, stage=None, file_pattern=None) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker
    how_much_down = 19

    # pilot.app.reload_ui()
    if isinstance(data_path, Path):
        data_path = str(data_path)
    if isinstance(work_dir_path, Path):
        work_dir_path = str(work_dir_path)
    if isinstance(file_pattern, Path):
        file_pattern = str(file_pattern)
    # Delete work_dir if exists
    if os.path.exists(work_dir_path):
        shutil.rmtree(work_dir_path)
    logger.info(f"Setting data path: {data_path}, work dir path: {work_dir_path}")

    # Define functions to execute based on stage requirements
    async def add_dual_reg_task():
        await add_new_feature(pilot, feature_type="dual_reg", label="dual_reg_1")
        # select all images
        await select_images(pilot)
        # Add map file pattern
        await add_atlas_or_seed_or_map_file_pattern(pilot, file_pattern)
        await select_file_tags(pilot, [1])

    async def final_stage_tasks():
        await check_and_run_tab_refresh(pilot)
        await settable_scroll_screen_down(pilot, how_much_down)
        # os.rename(Path(work_dir_path) / "spec.json", Path(work_dir_path) / f"spec_{stage}.json")

    # Map stages to the tasks they should trigger
    tasks_by_stage = {
        "at_features_tab": [add_dual_reg_task],
        "at_spec_preview": [add_dual_reg_task, final_stage_tasks],
    }

    # Execute tasks based on the specified stage
    # set work dir
    await _set_work_dir(pilot, work_dir_path)
    # set data dir
    await _load_data(pilot, data_path)
    # click Ok on Modal informing us that all data and workdir are set and user can proceed further
    await click_until_gone(pilot, "#only_one_button")

    for task in tasks_by_stage[stage]:
        await task()


@pytest.mark.forked
def test_dual_reg_at_features_tab(
    snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path, atlases_maps_seed_images_path: Path
) -> None:
    """Add file pattern of the map in dual regression feature. This triggers a modals about the meta information,
    if all goes Ok then there should be the file pattern of the map. Moreover, smoothing, grand mean scalling and
    temporal filters are set to Off."""

    map_file_pattern = atlases_maps_seed_images_path / "FIND_{map}_maps_2009.nii.gz"
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        file_pattern=map_file_pattern,
        stage="at_features_tab",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_dual_reg_at_spec_preview(
    snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path, atlases_maps_seed_images_path: Path
) -> None:
    """Same as test_dual_reg_at_features_tab but now we check the spec preview if the map pattern propagated to the spec
    file."""

    map_file_pattern = atlases_maps_seed_images_path / "FIND_{map}_maps_2009.nii.gz"
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        file_pattern=map_file_pattern,
        stage="at_spec_preview",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


#
