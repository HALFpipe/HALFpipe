# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    BaseInterfaceInputSpec,
    isdefined
)

import nibabel as nib
import numpy as np

from ..utils import nvol
from ..transformer import Transformer


class GrandMeanScalingInputSpec(BaseInterfaceInputSpec):
    in_files = traits.List(traits.File(exists=True), mandatory=True)
    mask_file = traits.File(exists=True, desc="3D brain mask")
    grand_mean = traits.Float(mandatory=True, desc="grand mean scale value")


class GrandMeanScalingOutputSpec(TraitedSpec):
    out_files = traits.List(traits.File(exists=True))


class GrandMeanScaling(Transformer):
    """
    Scale voxel values in every image by dividing
    the average global mean intensity of the whole session.
    """

    input_spec = GrandMeanScalingInputSpec
    output_spec = GrandMeanScalingOutputSpec

    suffix = "grandmeanscaled"

    def _transform(self, array):
        if self.scaling_factor is None:  # scaling factor is determined by first file
            self.scaling_factor = (
                self.inputs.grand_mean
                / array.mean()
            )

        array2 = array * self.scaling_factor

        return array2

    def _run_interface(self, runtime):
        in_files = self.inputs.in_files

        if not isdefined(in_files):
            return runtime

        mask_file = self.inputs.mask_file

        for in_file in in_files:
            self.in_img = None
            array = self._load(in_file)

            if self.in_img is not None and isdefined(mask_file):
                in_img = self.in_img

                mask_img = nib.load(mask_file)

                assert nvol(mask_img) == 1
                assert np.allclose(mask_img.affine, in_img.affine)

                mask_bdata = np.asanyarray(mask_img.dataobj).astype(np.bool)
                mask = np.ravel(mask_bdata)

                assert mask.size == array.shape[0]
            else:
                mask = np.ones((array.shape[0],), dtype=np.bool)

            self.scaling_factor = None
            array2 = np.zeros_like(array)
            array2[mask, :] = self._transform(array[mask, :])

            self._dump(array2)

        return runtime
