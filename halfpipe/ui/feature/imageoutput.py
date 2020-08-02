# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from ..step import YesNoStep
from ..model import ModelsStep
from ..setting import get_setting_init_steps, get_setting_vals_steps

next_step_type = ModelsStep


class AddAnotherImageOutputStep(YesNoStep):
    header_str = f"Output another preprocessed image?"
    yes_step_type = None  # add later
    no_step_type = next_step_type


ImageOutputSettingValsStep = get_setting_vals_steps(AddAnotherImageOutputStep)

ImageOutputSettingInitStep = get_setting_init_steps(
    ImageOutputSettingValsStep, settingdict={"output_image": True}, namefun=None
)

AddAnotherImageOutputStep.yes_step_type = ImageOutputSettingInitStep


class ImageOutputStep(YesNoStep):
    header_str = f"Output a preprocessed image?"
    yes_step_type = ImageOutputSettingInitStep
    no_step_type = next_step_type
