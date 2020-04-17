# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""
from os import path as op

import numpy as np
import nibabel as nib
from nilearn.image import resample_img

from nipype.interfaces.base import (
    BaseInterface,
    TraitedSpec,
    BaseInterfaceInputSpec,
    traits,
)

from ..utils import splitext


class ResampleIfNeededInputSpec(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Image file(s) to resample", exists=True, mandatory=True)
    ref_file = traits.File(desc="Reference file", exists=True, mandatory=True)
    method = traits.Enum("continuous", "linear", "nearest", default="continuous")


class ResampleIfNeededOutputSpec(TraitedSpec):
    out_file = traits.File()


class ResampleIfNeeded(BaseInterface):
    input_spec = ResampleIfNeededInputSpec
    output_spec = ResampleIfNeededOutputSpec

    def _run_interface(self, runtime):
        self._out_file = self.inputs.in_file

        in_img = nib.load(self.inputs.in_file)
        ref_img = nib.load(self.inputs.ref_file)
        if not in_img.shape[:3] == ref_img.shape[:3]:
            if not np.allclose(in_img.affine, ref_img.affine):
                resampled_img = resample_img(
                    in_img,
                    interpolation=self.inputs.method,
                    target_shape=ref_img.shape[:3],
                    target_affine=ref_img.affine,
                )
                basename, _ = splitext(op.basename(self._out_file))
                self._out_file = op.abspath(f"{basename}_res.nii.gz")
                nib.save(resampled_img, self._out_file)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()

        outputs["out_file"] = self._out_file
        return outputs
