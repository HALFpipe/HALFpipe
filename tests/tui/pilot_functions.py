# -*- coding: utf-8 -*-


async def _set_work_dir(pilot, work_dir_path) -> None:
    await pilot.press("w")
    # click on Browse
    await pilot.click(offset=(60, 15))
    # click to the prompt
    await pilot.click(offset=(74, 38))
    for letter in work_dir_path:
        await pilot.press(letter)
    # close the suggestion box (to see the Enter button
    await pilot.press("esc")
    # click on the Enter button
    await pilot.click(offset=(109, 41))
    # non existing path modal, click on "Ok"
    await pilot.click(offset=(117, 31))
    # Create new dir modal, click on "Ok"
    await pilot.click(offset=(100, 31))


async def _load_data(pilot, data_path) -> None:
    # switch to input data tab
    await pilot.press("i")
    # click on Browse button
    await pilot.click(offset=(60, 20))
    # click to the prompt
    await pilot.click(offset=(80, 38))
    # type in the path
    for letter in data_path:
        await pilot.press(letter)
    # close the suggestion box (to see the Enter button
    await pilot.press("esc")
    # click on the Enter button
    await pilot.click(offset=(110, 41))


async def add_new_feature(pilot, feature_type=None, label=None) -> None:
    feature_type = feature_type if feature_type is not None else "task_based"
    label = label if label is not None else "task_based_1"

    feature_type_yposition = {
        "task_based": 19,
        "seed_based": 21,
        "dual_reg": 23,
        "atlas": 25,
        "reho": 27,
        "falff": 29,
        "preproc": 31,
    }
    # select feature tab
    await pilot.press("f")
    # click on New button
    await pilot.click(offset=(10, 8))
    # click on Task based
    await pilot.click(offset=(100, feature_type_yposition[feature_type]))
    # click in the prompt
    await pilot.click(offset=(94, 25))
    for letter in label:
        await pilot.press(letter)
    # click on Ok button
    await pilot.click(offset=(100, 30))


async def select_images(pilot) -> None:
    # select all images
    await pilot.click(offset=(72, 9))
    await pilot.click(offset=(71, 10))
    await pilot.click(offset=(71, 11))
    await pilot.pause()


async def deselect_conditions(pilot, offset_y=0) -> None:
    # deselect one of the conditions
    await pilot.click(offset=(71, 18 + offset_y))


async def add_contrast_value_column(pilot, label=None, offset_y=0) -> None:
    label = "con1" if label is None else label
    # # click on Add contrast values
    await pilot.click(offset=(108, 38 + offset_y))
    # click in the prompt, for some reasons sometimes needs to be clicked twice
    await pilot.click(offset=(99, 16))
    await pilot.click(offset=(99, 16))
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


async def delete_column(pilot) -> None:
    await pilot.click(offset=(136, 38))


async def scroll_screen_down(pilot) -> None:
    # scroll screen
    await pilot.click(offset=(202, 50))


async def preprocessing_options(pilot) -> None:
    # set smoothing
    await pilot.click(offset=(130, 22))
    await pilot.press("backspace")
    await pilot.press("9")

    # grand mean scaling
    await pilot.click(offset=(134, 25))
    for _i in range(7):
        await pilot.press("backspace")
    for i in "12345":
        await pilot.press(i)

    # switch to frequency based
    await pilot.click(offset=(150, 28))
    await pilot.click(offset=(138, 32))

    # low
    await pilot.click(offset=(131, 31))
    for _i in range(5):
        await pilot.press("backspace")
    await pilot.press("8")
    # high
    await pilot.press("tab")
    await pilot.press("tab")
    for _i in range(5):
        await pilot.press("backspace")
    await pilot.press("9")


async def remove_confounds(pilot) -> None:
    # make few 'Remove confounds" options
    await pilot.click(offset=(71, 39))
    await pilot.click(offset=(71, 42))
    await pilot.click(offset=(71, 46))


async def check_and_run_tab_refresh(pilot) -> None:
    await pilot.press("r")
    # refresh
    await pilot.click(offset=(83, 9))
    # # save
    await pilot.click(offset=(100, 9))
    # press 'Ok' to dismiss the modal
    await pilot.click(offset=(117, 31))


async def scroll_screen_down_spec(pilot) -> None:
    # scroll screen (different layout than in features)
    await pilot.click(offset=(200, 49))


async def toggle_bids_non_bids(pilot) -> None:
    # toggle bids to non bids
    await pilot.click(offset=(113, 14))


async def fill_path_pattern_modal(pilot, path_patter):
    # clear all
    await pilot.click(offset=(120, 30))
    # click to prompt
    await pilot.click(offset=(60, 22))
    for i in path_patter:
        await pilot.press(i)
    # click Ok
    await pilot.click(offset=(125, 40))


async def set_non_bids_data(pilot, t1_pattern_path=None, bold_pattern_path=None) -> None:
    await pilot.press("i")

    # toggle bids to non bids

    await pilot.click(offset=(113, 14))

    # add T1
    await pilot.click(offset=(57, 35))
    # clear all
    await pilot.click(offset=(120, 30))
    # click to prompt
    await pilot.click(offset=(60, 22))
    # t1_pattern_path = '/tmp/tui_test/ds002785/sub-{subject}/anat/sub-{subject}_T1w.nii.gz'
    for i in t1_pattern_path:
        await pilot.press(i)
    await pilot.click(offset=(125, 40))

    # add bold
    await pilot.click(offset=(57, 46))
    # clear all
    await pilot.click(offset=(120, 30))
    # click to prompt
    await pilot.click(offset=(60, 22))

    # bold_pattern_path = '/tmp/tui_test/ds002785/sub-{subject}/func/sub-{subject}_task-{task}_bold.nii.gz'
    for i in bold_pattern_path:
        await pilot.press(i)
    # clear ok
    await pilot.click(offset=(125, 40))
    # click Ok on Repetition time values
    await pilot.click(offset=(100, 31))

    # focus on the scroll bar
    await pilot.click(offset=(100, 31))
    for _i in range(15):
        await pilot.press("down")
    # click confirm
    await pilot.click(offset=(100, 47))


async def settable_scroll_screen_down(pilot, how_much=20) -> None:
    # scroll screen (different layout than in features)
    for _i in range(how_much):
        await pilot.press("down")
