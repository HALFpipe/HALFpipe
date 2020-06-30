# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File,
    BaseInterfaceInputSpec,
)

import nibabel as nib
import numpy as np

from nipype.utils.filemanip import fname_presuffix
from nilearn.image import new_img_like

from ..utils import nvol


class GrandMeanScalingInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="input BOLD time-series (4D file)")
    mask_file = File(exists=True, mandatory=True, desc="3D brain mask")
    grand_mean = traits.Float(mandatory=True, desc="grand mean scale value")


class GrandMeanScalingOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="scaled BOLD time-series (4D file)")


class GrandMeanScaling(SimpleInterface):
    """
    Scale voxel values in every image by dividing
    the average global mean intensity of the whole session.
    """

    input_spec = GrandMeanScalingInputSpec
    output_spec = GrandMeanScalingOutputSpec

    def _run_interface(self, runtime):
        in_img = nib.load(self.inputs.in_file)

        mask_img = nib.load(self.inputs.mask_file)

        assert nvol(mask_img) == 1
        assert mask_img.shape[:3] == in_img.shape[:3]
        assert np.allclose(mask_img.affine, in_img.affine)

        img_vals = in_img.get_fdata()

        scaling_factor = (
            self.inputs.grand_mean
            / img_vals[np.asanyarray(mask_img.dataobj).astype(np.bool)].mean()
        )

        img_vals *= scaling_factor

        out = fname_presuffix(self.inputs.in_file, suffix="_grandmeanscaled")

        outimg = new_img_like(in_img, img_vals)
        nib.save(outimg, out)

        self._results["out_file"] = out

        return runtime
