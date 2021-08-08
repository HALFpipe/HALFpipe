# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing_extensions import Final


class constants:
    reference_space: Final[str] = "MNI152NLin2009cAsym"
    reference_res: Final[int] = 2

    workflowdir: Final[str] = "nipype"

    grayord_density: Final[str] = "91k"
