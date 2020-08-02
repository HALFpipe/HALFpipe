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
    SimpleInterface,
    TraitedSpec,
    traits,
)

from ..utils import splitext


class ResampleInputSpec(TraitedSpec):
    in_file = traits.File(desc="Image file(s) to resample", exists=True, mandatory=True)
    ref_file = traits.File(desc="Reference file", exists=True, mandatory=True)
    method = traits.Enum("continuous", "linear", "nearest", default="continuous")
    lazy = traits.Bool(default=True, usedefault=True, desc="only resample if necessary")


class ResampleOutputSpec(TraitedSpec):
    out_file = traits.File()


class Resample(SimpleInterface):
    input_spec = ResampleInputSpec
    output_spec = ResampleOutputSpec

    def _run_interface(self, runtime):
        out_file = self.inputs.in_file

        in_img = nib.load(self.inputs.in_file)
        ref_img = nib.load(self.inputs.ref_file)

        if not in_img.shape[:3] == ref_img.shape[:3] or not np.allclose(
            in_img.affine, ref_img.affine
        ) or not self.inputs.lazy:
            resampled_img = resample_img(
                in_img,
                interpolation=self.inputs.method,
                target_shape=ref_img.shape[:3],
                target_affine=ref_img.affine,
            )
            basename, _ = splitext(op.basename(self._out_file))

            out_file = op.abspath(f"{basename}_res.nii.gz")

            nib.save(resampled_img, out_file)

        self._results["out_file"] = out_file

        return runtime
