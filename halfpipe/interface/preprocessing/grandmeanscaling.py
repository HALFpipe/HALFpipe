# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    BaseInterfaceInputSpec,
    isdefined
)

from ..transformer import Transformer


class GrandMeanScalingInputSpec(BaseInterfaceInputSpec):
    files = traits.List(traits.File(exists=True), mandatory=True)
    mask = traits.File(exists=True, desc="3D brain mask")
    mean = traits.Float(mandatory=True, desc="grand mean scale value")


class GrandMeanScalingOutputSpec(TraitedSpec):
    files = traits.List(traits.File(exists=True))


class GrandMeanScaling(Transformer):
    """
    Scale voxel values in every image by dividing
    the average global mean intensity of the whole session.
    Applies the scaling factor of the first file to the other files
    in in_files
    """

    input_spec = GrandMeanScalingInputSpec
    output_spec = GrandMeanScalingOutputSpec

    suffix = "grandmeanscaled"

    def _transform(self, array):
        if self.scaling_factor is None:  # scaling factor is determined by first file
            self.scaling_factor = (
                self.inputs.mean
                / array.mean()
            )

        array2 = array * self.scaling_factor

        return array2

    def _run_interface(self, runtime):
        in_files = self.inputs.files

        if not isdefined(in_files):
            return runtime

        out_files = []

        for in_file in in_files:
            self.in_img = None
            array = self._load(in_file)

            self.scaling_factor = None
            array2 = self._transform(array)

            out_file = self._dump(array2)
            out_files.append(out_file)

        self._results["files"] = out_files

        return runtime
