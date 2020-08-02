# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from ..step import YesNoStep


class AddAnotherModelStep(YesNoStep):
    header_str = "Add another group-level model?"
    yes_step_type = None  # add later, because not yet defined
    no_step_type = None
