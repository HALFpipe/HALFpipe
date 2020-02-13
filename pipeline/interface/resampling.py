# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.ants.resampling import (
    ApplyTransformsInputSpec,
    ApplyTransformsOutputSpec
)

from nipype.interfaces.base import (
    BaseInterface
)


class DontApplyTransforms(BaseInterface):
    input_spec = ApplyTransformsInputSpec
    output_spec = ApplyTransformsOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["output_image"] = self.inputs.input_image
        return outputs
