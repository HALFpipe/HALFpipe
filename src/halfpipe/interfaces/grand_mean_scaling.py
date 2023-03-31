# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging

import numpy as np
from nipype.interfaces.base import (
    BaseInterfaceInputSpec,
    File,
    TraitedSpec,
    isdefined,
    traits,
)

from .transformer import Transformer


class GrandMeanScalingInputSpec(BaseInterfaceInputSpec):
    files = traits.List(File(exists=True), mandatory=True)
    mask = File(exists=True, desc="3D brain mask")
    mean = traits.Float(mandatory=True, desc="grand mean scale value")


class GrandMeanScalingOutputSpec(TraitedSpec):
    files = traits.List(File(exists=True))


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
            arraymean = np.nanmean(array)
            if arraymean == 0:
                logging.getLogger("halfpipe").warning(
                    f'File "{self.inputs.files[0]}" has a grand mean of 0. Skipping grand mean scaling'
                )
                self.scaling_factor = 1.0
            else:
                self.scaling_factor = self.inputs.mean / arraymean

        array2 = array * self.scaling_factor

        return array2

    def _run_interface(self, runtime):
        in_files = self.inputs.files
        self.scaling_factor = None

        if not isdefined(in_files):
            return runtime

        out_files = []

        for in_file in in_files:
            self.in_img = None
            array = self._load(in_file)

            array2 = self._transform(array)

            out_file = self._dump(array2)
            out_files.append(out_file)

        self._results["files"] = out_files

        return runtime
