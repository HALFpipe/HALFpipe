# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from ..step import YesNoStep
from ..setting import get_setting_vals_steps
from .imageoutput import ImageOutputStep


class AddAnotherFeatureStep(YesNoStep):
    header_str = f"Add another first-level feature?"
    yes_step_type = None  # add later
    no_step_type = ImageOutputStep


SettingValsStep = get_setting_vals_steps(AddAnotherFeatureStep)
