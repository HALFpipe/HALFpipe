# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from ..utils import YesNoStep
from ..higherlevel import GroupLevelAnalysisStep


class AddAnotherFirstLevelAnalysisStep(YesNoStep):
    header_str = f"Add another subject-level analysis?"
    yes_step_type = None  # add later
    no_step_type = GroupLevelAnalysisStep
