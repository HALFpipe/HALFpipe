# -*- coding: utf-8 -*-
import os
import shutil
from pathlib import Path

from halfpipe.logging import logger
from textual.css.query import InvalidQueryFormat, NoMatches, TooManyMatches, WrongType


async def _load_data(pilot, data_path) -> None:
    try:
        # switch to input data tab
        await pilot.press("i")
        # await pilot.click(offset=(60, 20))
        # here we need to change scope since the browse button is nested under the data_input_file_browser
        await pilot.click(pilot.app.get_widget_by_id("data_input_file_browser").get_widget_by_id("file_browser_edit_button"))
        await enter_browse_path(pilot, data_path)
        # click Ok on Modal informing us that the data input is success
        # await pilot.click(offset=(121, 31))
        # await pilot.pause(3)
        # await pilot.wait_for_scheduled_animations()
        await pilot.click("#only_one_button")
        # await pilot.wait_for_scheduled_animations()
        logger.debug("Bids data directory is set.")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)
    # await pilot.wait_for_scheduled_animations()
    # this part is to safely dismiss load screen
    load_modal = True
    while load_modal:
        try:
            load_modal_widget = pilot.app.get_widget_by_id('load_modal_panel')
            await pilot.app.pop_screen()
            load_modal = True
        except NoMatches:
            load_modal = False

async def _set_work_dir(pilot, work_dir_path, load_from_spec_file=False) -> None:
    try:
        await pilot.press("w")
        # click on Browse button
        # await pilot.click(offset=(60, 15))
        # here we need to change scope since the browse button is nested under the data_input_file_browser
        await pilot.click(pilot.app.get_widget_by_id("work_dir_file_browser").get_widget_by_id("file_browser_edit_button"))
        await enter_browse_path(pilot, work_dir_path)
        if not load_from_spec_file:
            # non existing path modal, click on "Ok"
            # await pilot.click(offset=(117, 31))
            await pilot.click("#only_one_button")
            # Create new dir modal, click on "Ok"
            # await pilot.click(offset=(100, 31))
            await pilot.click("#ok_left_button")
        else:
            # Spec file found modal, click Load
            # await pilot.click(offset=(100, 31))
            await pilot.click("#ok_left_button")
            # click ok on modal informing us that all went ok
            await pilot.click("#only_one_button")
        await pilot.click("#only_one_button")

        logger.debug(f"UI tests -> work directory is set to {work_dir_path}")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)
    await pilot.wait_for_scheduled_animations()


async def enter_browse_path(pilot, path):
    # click to the prompt
    # await pilot.click(offset=(80, 38))
    await pilot.click("#input_prompt")
    logger.debug(f"Entering browse path: {path}")
    for _i in range(4):
        await pilot.press("backspace")
        await pilot.press("delete")

    # type in the path
    for letter in path:
        await pilot.press(letter)
    # close the suggestion box (to see the Enter button
    await pilot.press("esc")
    # click on the Enter button
    # await pilot.click(offset=(110, 41))
    await pilot.click("#ok_button")
    logger.debug("UI tests -> The browse path is set.")


async def _select_covariates_spreadsheet(pilot, spreadsheet_path):
    # click 'Add'
    # await pilot.click(offset=(78, 40))
    await pilot.click("#add_spreadsheet")
    # click Browse
    # await pilot.click(offset=(55, 26))
    await pilot.click("#browse")
    # enter the path
    logger.debug(f"UI tests -> The spreadsheet path: {spreadsheet_path}")

    await enter_browse_path(pilot, spreadsheet_path)
    # set sex as categorical
    # await pilot.click(offset=(119, 32))
    await pilot.click(pilot.app.get_widget_by_id("row_radio_sets_3").get_widget_by_id("radio_column_2"))
    # set site as categorical
    # await pilot.click(offset=(119, 34))
    await pilot.click(pilot.app.get_widget_by_id("row_radio_sets_4").get_widget_by_id("radio_column_2"))
    # click Ok
    # await pilot.click(offset=(129, 43))
    await pilot.click("#ok")


async def _select_group_level_models_cutoffs_values(pilot):
    ### set mean value
    # click in the prompt
    # await pilot.click(offset=(136, 24))
    await pilot.click(pilot.app.get_widget_by_id("cutoff_panel").get_widget_by_id("cutoff_fd_mean"))
    # delete prompt
    for _i in range(4):
        await pilot.press("backspace")
        await pilot.press("delete")
    # type new value
    for i in "0.25":
        await pilot.press(i)
    ### set percentage value
    # click in the prompt
    # await pilot.click(offset=(136, 27))
    await pilot.click(pilot.app.get_widget_by_id("cutoff_panel").get_widget_by_id("cutoff_fd_perc"))
    # delete prompt
    for _i in range(4):
        await pilot.press("backspace")
        await pilot.press("delete")
    # type new value
    for i in "15":
        await pilot.press(i)


async def add_new_feature(pilot, feature_type=None, label=None, tab_type="f") -> None:
    try:
        feature_type = feature_type if feature_type is not None else "task_based"
        label = label if label is not None else "task_based_1"

        feature_type_yposition = {
            "task_based": 0,
            "seed_based": 1,
            "dual_reg": 2,
            "gigica": 3,
            "atlas": 4,
            "reho": 5,
            "falff": 6,
            "preproc": 7,
            "intercept_only": 0,
            "linear_model": 1,
        }
        # select feature tab
        await pilot.press(tab_type)
        # click on New button
        # await pilot.click(offset=(10, 8))
        # await pilot.click("#new_item_button")
        if tab_type == "f":
            await pilot.click(pilot.app.get_widget_by_id("feature_selection_content").get_widget_by_id("new_item_button"))
        elif tab_type == "g":
            await pilot.click(pilot.app.get_widget_by_id("models_content").get_widget_by_id("new_item_button"))

        # click on Task based
        # await pilot.click(offset=(100, feature_type_yposition[feature_type]))
        await pilot.click("#options")
        for _i in range(feature_type_yposition[feature_type]):
            await pilot.press("down")
        await pilot.press("enter")

        # click in the prompt
        # await pilot.click(offset=(94, 25))
        await pilot.click("#feature_name")
        for letter in label:
            await pilot.press(letter)
        # click on Ok button
        # await pilot.click(offset=(100, 30))
        await pilot.click("#ok")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


async def select_images(pilot) -> None:
    try:
        await pilot.click("#tasks_to_use_selection")
        # select all images
        # await pilot.click(offset=(71, 9))
        # await pilot.click(offset=(71, 10))
        # await pilot.click(offset=(71, 11))
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


async def deselect_image(pilot, which_one=2) -> None:
    await pilot.click("#tasks_to_use_selection")
    for _i in range(which_one):
        await pilot.press("down")
    await pilot.press("enter")


async def deselect_conditions(pilot, offset_y=2) -> None:
    try:
        # deselect one of the conditions
        # await pilot.click(offset=(71, 23 + offset_y))
        await pilot.click("#model_conditions_selection")
        for _i in range(offset_y):
            await pilot.press("down")
        await pilot.press("enter")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


async def add_contrast_value_column(pilot, label=None, offset_y=0) -> None:
    try:
        label = "con1" if label is None else label
        # # click on Add contrast values
        # await pilot.click(offset=(108, 43 + offset_y))
        await pilot.click("#add_contrast_values_button")
        # click in the prompt, for some reasons sometimes needs to be clicked twice
        # await pilot.click(offset=(99, 16))
        # await pilot.click(offset=(99, 16))
        await pilot.click("#contrast_name")
        for letter in label:
            await pilot.press(letter)
        await pilot.press("tab")
        await pilot.press("1")
        await pilot.press("tab")
        await pilot.press("2")
        await pilot.press("tab")
        await pilot.press("3")
        await pilot.press("tab")
        await pilot.press("4")
        await pilot.press("tab")
        await pilot.press("5")
        await pilot.press("tab")
        await pilot.press("6")
        await pilot.press("tab")
        await pilot.press("enter")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


async def delete_column(pilot) -> None:
    try:
        # await pilot.click(offset=(136, 43))
        await pilot.click(
            pilot.app.get_widget_by_id("model_conditions_and_constrasts").get_widget_by_id("delete_contrast_values_button")
        )
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


# async def scroll_screen_down(pilot) -> None:
#     # scroll screen
#     await pilot.click(offset=(202, 50))


async def set_grand_mean_scaling(pilot, value="12345"):
    await pilot.click(pilot.app.get_widget_by_id("grand_mean_scaling").get_widget_by_id("input_switch_input_box"))
    await clear_entry(pilot)

    for i in value:
        await pilot.press(i)


async def toggle_grand_mean_scaling(pilot):
    await pilot.click(pilot.app.get_widget_by_id("grand_mean_scaling").get_widget_by_id("the_switch"))


async def set_bandpass_filter_type_to_frequency_based(pilot):
    await pilot.click(pilot.app.get_widget_by_id("bandpass_filter_type").get_widget_by_id("input_switch_input_box"))
    await pilot.press("down")
    await pilot.press("enter")


async def toggle_bandpass_filter(pilot):
    await pilot.click(pilot.app.get_widget_by_id("bandpass_filter_type").get_widget_by_id("the_switch"))


async def set_bandpass_filter_lp_width(pilot, value="8"):
    await pilot.click(pilot.app.get_widget_by_id("bandpass_filter_lp_width").get_widget_by_id("input_switch_input_box"))
    await clear_entry(pilot)
    for v in value:
        await pilot.press(v)


async def set_bandpass_filter_hp_width(pilot, value="9"):
    await pilot.click(pilot.app.get_widget_by_id("bandpass_filter_hp_width").get_widget_by_id("input_switch_input_box"))
    await clear_entry(pilot)
    for v in value:
        await pilot.press(v)


async def set_smoothing(pilot, value="9"):
    await pilot.click(pilot.app.get_widget_by_id("smoothing").get_widget_by_id("input_switch_input_box"))
    await clear_entry(pilot)
    for v in value:
        await pilot.press(v)


async def toggle_smoothing(pilot):
    await pilot.click(pilot.app.get_widget_by_id("smoothing").get_widget_by_id("the_switch"))


async def preprocessing_options(pilot) -> None:
    # set smoothing
    # await pilot.click(offset=(130, 22))
    await set_smoothing(pilot)

    # grand mean scaling
    # await pilot.click(offset=(134, 25))
    await set_grand_mean_scaling(pilot)

    # # switch to frequency based
    # # await pilot.click(offset=(150, 28))
    await set_bandpass_filter_type_to_frequency_based(pilot)

    # low
    # await pilot.click(offset=(131, 31))
    await set_bandpass_filter_lp_width(pilot)

    # high
    await set_bandpass_filter_hp_width(pilot)


async def remove_confounds(pilot) -> None:
    # make few 'Remove confounds" options
    await pilot.click("#confounds_selection")
    await pilot.press("enter")
    for _i in range(3):
        await pilot.press("down")
    await pilot.press("enter")
    for _i in range(5):
        await pilot.press("down")
    await pilot.press("enter")
    for _i in range(3):
        await pilot.press("down")
    # await pilot.click(offset=(71, 39))
    # await pilot.click(offset=(71, 42))
    # await pilot.click(offset=(71, 47))


async def check_and_run_tab_refresh(pilot) -> None:
    # random click before scroll
    await pilot.click(offset=(50, 10))
    await pilot.press("r")
    # save
    # await pilot.click(offset=(100, 9))
    # await pilot.click("#save_button")
    # press 'Ok' to dismiss the modal
    # await pilot.click(offset=(117, 31))
    # await pilot.click("#only_one_button")


# async def scroll_screen_down_spec(pilot) -> None:
#     # scroll screen (different layout than in features)
#     await pilot.click(offset=(200, 49))


async def toggle_bids_non_bids(pilot) -> None:
    # toggle bids to non bids
    # await pilot.click(offset=(113, 14))
    # await pilot.click("#bids_non_bids_switch")
    await pilot.click(pilot.app.get_widget_by_id("input_data_content").get_widget_by_id("bids_non_bids_switch"))


# async def fill_path_pattern_modal(pilot, path_patter):
#     # clear all
#     await pilot.click(offset=(120, 30))
#     # click to prompt
#     await pilot.click(offset=(60, 22))
#     for i in path_patter:
#         await pilot.press(i)
#     # click Ok
#     await pilot.click(offset=(125, 40))


async def add_t1(pilot, t1_pattern_path) -> None:
    ### add T1
    # await pilot.click(offset=(57, 35))
    await pilot.click("#add_t1_image_button")
    # set the path pattern
    await set_path_in_path_pattern_builder(pilot, t1_pattern_path)
    await pilot.click(pilot.app.get_widget_by_id("ok_left_button"))


async def add_bold(pilot, bold_pattern_path, set_repetition_time) -> None:
    ### add bold
    # await pilot.click(offset=(57, 46))
    await pilot.click("#add_bold_image_button")
    # set the path pattern
    await set_path_in_path_pattern_builder(pilot, bold_pattern_path)

    if set_repetition_time is True:
        # click No on 'Proceed with these values modal' (Repetition time values)
        # await pilot.click(offset=(116, 31))
        await pilot.click("#cancel_right_button")

        # Specify repetition time in seconds: Click into prompt
        # await pilot.click(offset=(96, 27))
        await pilot.click("#input_prompt")
        await clear_entry(pilot)
        # Set time to '9'
        await pilot.press("9")
        # Click Ok to dismiss
        # await pilot.click(offset=(96, 31))
        await pilot.click("#only_one_button")
    else:
        # click Ok
        # await pilot.click(offset=(100, 31))
        await pilot.click(pilot.app.get_widget_by_id("ok_left_button"))


async def add_fmap(pilot, phase_diff_fmap_pattern, magnitude_fmap_pattern) -> None:
    try:
        await pilot.click("#add_field_map_button")
        # select 'Siemens' by focusing and going one down and confirming with enter
        # await pilot.press("tab")
        await pilot.press("down")
        # await pilot.press("down")

        await pilot.press("enter")
        # # confirm choice of the whole window
        await pilot.click("#ok")
        # # confirm that we want one magnitude file and one phase difference file
        await pilot.click("#ok")
        # # enter path pattern for phase difference files
        # # await sleep(5)
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)

    await set_path_in_path_pattern_builder(pilot, str(phase_diff_fmap_pattern))

    try:
        # now there is a modal with prompt for entering the echo time value, we enter there some value
        for i in range(1, 3):
            # now there should be a modal informing that first echo times are missing, we dismiss it
            await pilot.click("#only_one_button")
            await pilot.click("#input_prompt")
            await clear_entry(pilot)
            # Set echo time to '1'
            await pilot.press(str(i))
            # Click Ok to dismiss
            await pilot.click("#only_one_button")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)
    #
    await set_path_in_path_pattern_builder(pilot, str(magnitude_fmap_pattern))
    #
    # await settable_scroll_screen_down(pilot, 10)


async def clear_entry(pilot) -> None:
    for _i in range(20):
        await pilot.press("backspace")
        await pilot.press("delete")


async def associate_fmaps(pilot) -> None:
    try:
        await pilot.click("#associate_button")
        # since it our case there is nothing to associate we will get only the echo spacing missing modal,
        # dismiss it
        await pilot.click("#only_one_button")
        # enter some value
        await pilot.click("#input_prompt")
        await clear_entry(pilot)
        await pilot.press(str(9))

        await pilot.click("#only_one_button")
        # missing phase encoding direction modal
        # dismiss it
        await pilot.click("#only_one_button")
        # select some direction
        await pilot.press("tab")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.click("#ok")
        # click confirm
        await pilot.click("#confirm_non_bids_button")
        # click Ok on Modal informing us that the data input is success
        await pilot.click("#only_one_button")
        # Click Ok on Modal saying that data and workdir is set and user can proceed further
        await pilot.click("#only_one_button")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


async def set_non_bids_data(
    pilot, t1_pattern_path=None, bold_pattern_path=None, set_repetition_time=False, noconfirm=False
) -> None:
    logger.debug("UI tests -> Running function: set_non_bids_data")
    await pilot.press("i")

    ### toggle bids to non bids
    # await pilot.click(offset=(113, 14))
    # await pilot.click('#bids_non_bids_switch')
    try:
        await toggle_bids_non_bids(pilot)
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)

    await settable_scroll_screen_down(pilot, 30)

    try:
        await add_t1(pilot, t1_pattern_path)
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)
    try:
        await add_bold(pilot, bold_pattern_path, set_repetition_time)
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)

    await settable_scroll_screen_down(pilot, 15)
    #
    if not noconfirm:
        # click confirm
        # await pilot.click(offset=(100, 47))
        try:
            await pilot.click("#confirm_non_bids_button")
            # click Ok on Modal informing us that the data input is success
            await pilot.click("#only_one_button")
            # # Click Ok on Modal saying that data and workdir is set and user can proceed further
            await pilot.click("#only_one_button")
            await pilot.click("#only_one_button")

        except Exception as e:
            pilot.app.save_screenshot()
            logger.info(e)
    logger.debug("UI tests -> set_non_bids_data successful!")


async def set_path_in_path_pattern_builder(pilot, path_pattern) -> None:
    # clear all
    # await pilot.click(offset=(120, 30))
    try:
        logger.debug(f"UI tests -> Typing {path_pattern} in the path pattern builder")
        await pilot.click("#clear_all")
        # click to prompt
        # await pilot.click(offset=(60, 22))
        await pilot.click("#input_prompt")
        for i in path_pattern:
            await pilot.press(i)
        # press ok button
        # await pilot.click(offset=(125, 40))
        await pilot.click("#ok_button")
        logger.debug(f"UI tests -> Success! The path {path_pattern} was set in the path pattern builder.")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


async def settable_scroll_screen_down(pilot, how_much=19) -> None:
    # random click to focus the form
    await pilot.click(offset=(50, 10))
    # scroll screen (different layout than in features)
    for _i in range(how_much):
        await pilot.press("down")


async def run_before_for_reho_falff_preproc(
    pilot, data_path=None, work_dir_path=None, stage=None, file_pattern=None, feature_type=None
) -> None:
    # always reload the app first, there is some strange crossinteraction between tests, nothing else helped except using
    # -n 2 flag for the pytest, i.e., running each test with a separate worker
    how_much_down = 35

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
    logger.info(f"Setting data path: {data_path}, work dir path: {work_dir_path}, file pattern path: {file_pattern}")

    # Define functions to execute based on stage requirements
    async def add_feature():
        await add_new_feature(pilot, feature_type=feature_type, label=feature_type + "_1")
        # select all images
        await select_images(pilot)
        # deselect second image
        # await pilot.click(offset=(71, 10))
        await deselect_image(pilot)
        # await pilot.press("down")
        # await pilot.press("enter")

        # click in the Smoothing input box, delete the '0' and type '666'
        # await pilot.click(offset=(137, 22))
        # await pilot.press("backspace")
        # for i in "666":
        #     await pilot.press(i)
        await set_smoothing(pilot, value="666")

        # click in the Grand mean scaling input box, delete the '0' and type '666'
        # await pilot.click(offset=(137, 26))
        # for _i in range(7):
        #     await pilot.press("backspace")
        # for i in "12345":
        #     await pilot.press(i)
        await set_grand_mean_scaling(pilot)

        # click on the selection arrow of the temporal filter and select 'frequency_based'
        # await pilot.click(offset=(151, 28))
        # await pilot.click(offset=(151, 32))
        if feature_type not in ["falff", "reho"]:
            await set_bandpass_filter_type_to_frequency_based(pilot)

        # change low pass filter value to 0.019
        # await pilot.click(offset=(137, 31))
        # await pilot.press("9")
        await set_bandpass_filter_lp_width(pilot, value="0.019")

        # change high pass filter value to 0.19
        # await pilot.click(offset=(137, 34))
        # await pilot.press("9")
        await set_bandpass_filter_hp_width(pilot, value="0.19")

        # remove confounds (activate all)
        await remove_confounds_select_all(pilot)
        # await pilot.click(offset=(72, 39))
        # await pilot.click(offset=(72, 40))
        # await pilot.click(offset=(72, 41))
        # await pilot.click(offset=(72, 42))
        # await pilot.click(offset=(72, 43))
        # await pilot.click(offset=(72, 44))
        # await pilot.click(offset=(72, 45))
        # await pilot.click(offset=(72, 46))
        # await pilot.click(offset=(72, 47))
        # await pilot.click(offset=(72, 48))

    async def final_stage_tasks():
        await check_and_run_tab_refresh(pilot)
        await settable_scroll_screen_down(pilot, how_much_down)
        # os.rename(Path(work_dir_path) / "spec.json", Path(work_dir_path) / f"spec_{stage}.json")

    # Map stages to the tasks they should trigger
    tasks_by_stage = {
        "at_features_tab": [add_feature],
        "at_spec_preview": [add_feature, final_stage_tasks],
    }

    # Execute tasks based on the specified stage
    # set work dir
    await _set_work_dir(pilot, work_dir_path)
    # set data dir
    await _load_data(pilot, data_path)
    # click Ok on Modal informing us that all data and workdir are set and user can proceed further
    try:
        await pilot.click("#only_one_button")
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)

    for task in tasks_by_stage[stage]:
        await task()


async def remove_confounds_select_all(pilot) -> None:
    # make few 'Remove confounds" options
    await pilot.click("#confounds_selection")
    for _i in range(10):
        await pilot.press("enter")
        await pilot.press("down")


async def add_atlas_or_seed_or_map_file_pattern(pilot, file_pattern, event_file_pattern=False):
    # click on "Add" (atlas or seed image or map)
    # await pilot.click(offset=(76, 22))
    try:
        await pilot.click("#add_file_button")

        # select event file type if it is an event file pattern
        if event_file_pattern is True:
            await select_event_file_type(pilot)

        # add atlas file pattern
        # await fill_path_pattern_modal(pilot, file_pattern)
        await set_path_in_path_pattern_builder(pilot, file_pattern)

        # make choices of the space if it is not an event file pattern
        if event_file_pattern is False:
            await confirm_space_meta_data_after_selecting_file_pattern(pilot)
    except Exception as e:
        pilot.app.save_screenshot()
        logger.info(e)


async def select_event_file_type(pilot):
    # top_file_panel
    # Select event file type from the modal (tsv)
    # await pilot.click(offset=(86, 27))
    await pilot.click("#radio_set")
    await pilot.press("down")
    await pilot.press("down")
    await pilot.press("enter")
    # # Confirm modal by clicking OK
    # await pilot.click(offset=(96, 31))
    await pilot.click("#ok")


async def confirm_space_meta_data_after_selecting_file_pattern(pilot):
    # click No: Missing Space values modal (Found some values, proceed with those?: No because we want to test the
    # space selection modal (MNI ICBM 2009c vs. MNI ICB 152)).
    # await pilot.click(offset=(116, 31))
    await pilot.click("#only_one_button")

    # First item should be automatically selected, so we can click directly on "Ok"
    # await pilot.click(offset=(65, 26)) # this is first item in the selection, not used because of the reasons above
    # Click Ok
    # await pilot.click(offset=(131, 30))
    await pilot.click("#ok")


async def set_minimum_coverage(pilot, value="0.85"):
    await pilot.click(pilot.app.get_widget_by_id("minimum_coverage").get_widget_by_id("input_label_input_box"))
    for _i in range(5):
        await pilot.press("delete")
        await pilot.press("backspace")
    for v in value:
        await pilot.press(v)


async def select_file_tags(pilot, which_ones: list[int]):
    await pilot.click("#file_tag_selection")

    current_pos = 0  # start before first option

    for target in which_ones:
        # Move down until we reach the desired option
        moves = target - current_pos
        for _ in range(moves):
            await pilot.press("down")

        # Select it
        await pilot.press("enter")

        # Update current cursor position
        current_pos = target
