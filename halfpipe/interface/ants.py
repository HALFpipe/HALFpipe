# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import File

from nipype.interfaces.ants.resampling import ApplyTransformsInputSpec
from niworkflows.interfaces.fixes import FixHeaderApplyTransforms


class FixInputApplyTransformsInputSpec(ApplyTransformsInputSpec):
    input_image = File(
        argstr="--input %s",
        mandatory=False,
        desc="image to apply transformation to",
        exists=True,
    )


class FixInputApplyTransforms(FixHeaderApplyTransforms):
    input_spec = FixInputApplyTransformsInputSpec

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        if self.inputs.print_out_composite_warp_file:
            # Run normally
            runtime = super(FixHeaderApplyTransforms, self)._run_interface(
                runtime, correct_return_codes
            )
        else:
            # Run fixed
            runtime = super(FixInputApplyTransforms, self)._run_interface(
                runtime, correct_return_codes
            )

        return runtime
