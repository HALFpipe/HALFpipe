# -*- coding: utf-8 -*-

import os
from functools import partial
from pathlib import Path

from .pilot_functions import (
    _load_data,
    _set_work_dir,
    add_contrast_value_column,
    add_new_feature,
    check_and_run_tab_refresh,
    delete_column,
    deselect_conditions,
    preprocessing_options,
    remove_confounds,
    scroll_screen_down,
    scroll_screen_down_spec,
)

# this is for later
# from halfpipe import resource
# from halfpipe.resource import get as get_resource
#
# # set atlases, seed maps and spatial maps
# test_online_resources = {
#     "FIND_ica_maps_2009.nii.gz": "https://drive.google.com/file/d/1XnFGm9aCcTIuXgKZ71fDqATBJWAxkInO/view?usp=drive_link",
#     "tpl-MNI152NLin2009cAsym_atlas-schaefer2011Combined_dseg.nii": "https://drive.google.com/file/d/1CR0rjbznad-tkfVc1vrGKsKJg5_nrf5E/view?usp=drive_link",
#     "tpl-MNI152NLin2009cAsym_atlas-brainnetomeCombined_dseg.nii":"https://drive.google.com/file/d/1MYF4VaZrWmQXL1Jl3ZWMg1tWaKBfPo4W/view?usp=drive_link",
#     "R_vmPFC_seed_2009.nii.gz":"https://drive.google.com/file/d/16L_HXOrrMqw08BdGTOh7RTErNTVytyvS/view?usp=drive_link",
#     "R_vlPFC_pt_seed_2009.nii.gz":"https://drive.google.com/file/d/1fNr8ctHpTN8XJn95mclMxTetKdpbdddV/view?usp=drive_link",
#     "R_vlPFC_po_seed_2009.nii.gz":"https://drive.google.com/file/d/1te1g3tpFaHdjx8GyZ1myMg_ayaHXPYKO/view?usp=drive_link"
# }
# resource.online_resources.update(test_online_resources)
#
# # download them
# path = get_resource("FIND_ica_maps_2009.nii.gz")
# print(path)

# from ..workflows.datasets import Dataset


async def run_before(pilot, data_path=None, work_dir_path=None, stage=None) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker

    pilot.app.reload_ui()
    if isinstance(data_path, Path):
        data_path = str(data_path)
    if isinstance(work_dir_path, Path):
        work_dir_path = str(work_dir_path)
    print("----------------------------", data_path, work_dir_path)

    # Define functions to execute based on stage requirements
    async def add_feature_related_tasks():
        await add_new_feature(pilot)
        await deselect_conditions(pilot)
        await add_contrast_value_column(pilot, label="col1")
        await delete_column(pilot)
        await add_contrast_value_column(pilot, label="col2")

    async def feature_p2_and_final_tasks():
        await scroll_screen_down(pilot)
        await preprocessing_options(pilot)
        await remove_confounds(pilot)

    async def final_stage_tasks():
        await check_and_run_tab_refresh(pilot)
        await scroll_screen_down_spec(pilot)
        os.rename(Path(work_dir_path) / "spec.json", Path(work_dir_path) / "spec_task_based.json")

    # Map stages to the tasks they should trigger
    tasks_by_stage = {
        "features_task_based_p1": [add_feature_related_tasks],
        "features_task_based_p2": [add_feature_related_tasks, feature_p2_and_final_tasks],
        "features_task_based_final": [add_feature_related_tasks, feature_p2_and_final_tasks, final_stage_tasks],
    }

    # Execute tasks based on the specified stage
    # set work dir
    await _set_work_dir(pilot, work_dir_path)
    # set data dir
    await _load_data(pilot, data_path)
    for task in tasks_by_stage[stage]:
        await task()


# circumvent downloading the data since this will come later when the test itself is ok
# def test_task_based_features(
#     snap_compare, start_app, fixed_tmp_path: Path, work_dir_path: Path, downloaded_data_path: Path
# ) -> None:

# circumvent downloading the data since this will come later when the test itself is ok
# downloaded_data_path = "/home/tomas/github/HALFpipe/tests/workflows/bla"


def test_task_based_features_p1(snap_compare, start_app, work_dir_path: Path, downloaded_data_path: Path) -> None:
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="features_task_based_p1"
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_task_based_features_p2(
    snap_compare, start_app, fixed_tmp_path: Path, work_dir_path: Path, downloaded_data_path: Path
) -> None:
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="features_task_based_p2"
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_task_based_features_final(
    snap_compare, start_app, fixed_tmp_path: Path, work_dir_path: Path, downloaded_data_path: Path
) -> None:
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, work_dir_path=work_dir_path, stage="features_task_based_final"
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
