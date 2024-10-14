# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """

from ..setting import get_setting_vals_steps
from ..step import YesNoStep
from .imageoutput import ImageOutputStep


class AddAnotherFeatureStep(YesNoStep):
    header_str = "Add another first-level feature?"
    no_step_type = ImageOutputStep


SettingValsStep = get_setting_vals_steps(
    AddAnotherFeatureStep,
    noun="feature",
    vals_header_str="Specify preprocessing setting",
)
