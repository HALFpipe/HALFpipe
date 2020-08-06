# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import numpy as np

from nipype.interfaces import afni


class BlurInMask(afni.BlurInMask):
    """
    Lazy 3dBlurInMask
    """

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        self.blur = False

        if not np.isclose(self.inputs.fwhm, 0, atol=1e-2) or self.inputs.fwhm < 0:
            self.resample = True
            runtime = super(BlurInMask, self)._run_interface(
                runtime, correct_return_codes
            )

        return runtime

    def _list_outputs(self):
        if self.blur:
            outputs = super(BlurInMask, self)._list_outputs()
        else:
            outputs["out_file"] = self.inputs.in_file
        return outputs
