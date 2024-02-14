# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.ants.resampling import (
    ApplyTransformsInputSpec as NipypeApplyTransformsInputSpec,
)
from nipype.interfaces.base import File
from niworkflows.interfaces.fixes import FixHeaderApplyTransforms


class ApplyTransformsInputSpec(NipypeApplyTransformsInputSpec):
    input_image = File(
        argstr="--input %s",
        mandatory=False,
        desc="image to apply transformation to",
        exists=True,
    )


class ApplyTransforms(FixHeaderApplyTransforms):
    input_spec = ApplyTransformsInputSpec

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        if self.inputs.print_out_composite_warp_file:
            # Run normally
            runtime = super(FixHeaderApplyTransforms, self)._run_interface(runtime, correct_return_codes)
        else:
            # Run fixed
            runtime = super(ApplyTransforms, self)._run_interface(runtime, correct_return_codes)

        return runtime
