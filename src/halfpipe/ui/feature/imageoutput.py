# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..model import ModelsStep
from ..setting import get_setting_init_steps, get_setting_vals_steps
from ..step import YesNoStep

next_step_type = ModelsStep


class AddAnotherImageOutputStep(YesNoStep):
    header_str = "Output another preprocessed image?"
    no_step_type = next_step_type


ImageOutputSettingValsStep = get_setting_vals_steps(
    AddAnotherImageOutputStep, noun="image"
)

ImageOutputSettingInitStep = get_setting_init_steps(
    ImageOutputSettingValsStep,
    settingdict={"output_image": True},
    namefun=None,
    noun="image",
)

AddAnotherImageOutputStep.yes_step_type = ImageOutputSettingInitStep


class ImageOutputStep(YesNoStep):
    header_str = "Output a preprocessed image?"
    yes_step_type = ImageOutputSettingInitStep
    no_step_type = next_step_type
