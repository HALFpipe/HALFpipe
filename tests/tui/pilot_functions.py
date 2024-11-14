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


async def add_new_feature(pilot) -> None:
    # select feature tab
    await pilot.press("f")
    # click on New button
    await pilot.click(offset=(10, 8))
    # click on Task based
    await pilot.click(offset=(100, 19))
    # click in the prompt
    await pilot.click(offset=(94, 25))
    for letter in "task_based_1":
        await pilot.press(letter)
    # click on Ok button
    await pilot.click(offset=(100, 30))


async def select_images(pilot) -> None:
    # select all images
    await pilot.click(offset=(72, 9))
    await pilot.click(offset=(71, 10))
    await pilot.click(offset=(71, 11))
    await pilot.pause()


async def deselect_conditions(pilot) -> None:
    # deselect one of the conditions
    await pilot.click(offset=(71, 18))


async def add_contrast_value_column(pilot, label=None) -> None:
    label = "con1" if label is None else label
    # # click on Add contrast values
    await pilot.click(offset=(108, 38))
    # #
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
    # save
    await pilot.click(offset=(100, 9))
    # press 'Ok' to dismiss the modal
    await pilot.click(offset=(117, 31))


async def scroll_screen_down_spec(pilot) -> None:
    # scroll screen (different layout than in features)
    await pilot.click(offset=(200, 49))
