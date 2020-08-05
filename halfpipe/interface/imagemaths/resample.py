# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""
from pathlib import Path

import numpy as np
import nibabel as nib

from nipype.interfaces.ants.resampling import ApplyTransformsInputSpec
from niworkflows.interfaces.fixes import FixHeaderApplyTransforms

from nipype.interfaces.base import (
    traits,
)

from ...resource import get as getresource


class ResampleInputSpec(ApplyTransformsInputSpec):
    input_space = traits.Either("MNI152NLin6Asym", "MNI152NLin2009cAsym", mandatory=True)
    reference_space = traits.Either("MNI152NLin6Asym", "MNI152NLin2009cAsym", mandatory=True)
    lazy = traits.Bool(default=True, usedefault=True, desc="only resample if necessary")


class Resample(FixHeaderApplyTransforms):
    input_spec = ResampleInputSpec

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        self.resample = False

        input_image = nib.load(self.inputs.input_image)
        reference_image = nib.load(self.inputs.reference_image)
        input_matches_reference = input_image.shape[:3] == reference_image.shape[:3] and np.allclose(
            input_image.affine, reference_image.affine, atol=1e-2  # tolerance of 0.01 mm
        )

        input_space = self.inputs.input_space
        reference_space = self.inputs.reference_space

        transforms = "identity"
        if input_space != reference_space:
            xfm = getresource(f"tpl_{reference_space}_from_{input_space}_mode_image_xfm.h5")
            assert Path(xfm).is_file()
            transforms = [str(xfm)]

        self.inputs.transforms = transforms

        if not input_matches_reference or transforms != "identity" or not self.inputs.lazy:
            self.resample = True
            runtime = super(Resample, self)._run_interface(
                runtime, correct_return_codes
            )

        return runtime

    def _list_outputs(self):
        if self.resample:
            outputs = super(Resample, self)._list_outputs()
        else:
            outputs["output_image"] = self.input.input_image
        return outputs
