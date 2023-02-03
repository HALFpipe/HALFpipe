# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import nibabel as nib
import numpy as np
from nilearn.image import new_img_like
from nipype.interfaces.base import (
    DynamicTraitedSpec,
    File,
    InputMultiPath,
    OutputMultiPath,
    isdefined,
    traits,
)
from nipype.interfaces.io import IOBase, add_traits

from ...utils.path import split_ext


class MaskCoverageInputSpec(DynamicTraitedSpec):
    in_files = InputMultiPath(File(exists=True), desc="Input files", mandatory=True)

    mask_file = File(desc="Mask file", exists=True, mandatory=True)

    min_coverage = traits.Float(1.0)


class MaskCoverageOutputSpec(DynamicTraitedSpec):
    out_files = OutputMultiPath(File(exists=True))
    coverage = traits.List(traits.Float)


class MaskCoverage(IOBase):
    input_spec = MaskCoverageInputSpec
    output_spec = MaskCoverageOutputSpec

    def __init__(self, keys=[], **inputs):
        super(MaskCoverage, self).__init__(**inputs)
        self._keys = keys
        add_traits(self.inputs, keys)

    def _add_output_traits(self, base):
        return add_traits(base, self._keys)

    def _run_interface(self, runtime):
        mask_img = nib.load(self.inputs.mask_file)
        mask = np.asanyarray(mask_img.dataobj).astype(bool)
        mask = np.squeeze(mask)

        min_coverage = self.inputs.min_coverage
        if not isdefined(min_coverage) or not isinstance(min_coverage, float):
            min_coverage = 1.0
        self._min_coverage = min_coverage

        self._out_files = []
        self._coverage = []

        for in_file in self.inputs.in_files:
            in_img = nib.load(in_file)
            in_bool = np.asanyarray(in_img.dataobj).astype(bool)
            in_bool = np.squeeze(in_bool)

            unmasked_n_voxels = np.count_nonzero(in_bool)

            out_bool = np.logical_and(in_bool, mask)

            masked_n_voxels = np.count_nonzero(out_bool)

            coverage = float(masked_n_voxels) / float(unmasked_n_voxels)

            self._coverage.append(coverage)

            if coverage < min_coverage:
                self._out_files.append(None)

                continue

            stem, _ = split_ext(in_file)

            out_file = Path.cwd() / f"{stem}_masked.nii.gz"

            out_img = new_img_like(in_img, out_bool, copy_header=True)
            nib.save(out_img, out_file)

            self._out_files.append(out_file)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        outputs["out_files"] = []
        outputs["coverage"] = []

        for k in self._keys:
            outputs[k] = []

        for i in range(len(self._out_files)):
            if self._coverage[i] < self._min_coverage:
                continue  # omit from outputs

            outputs["out_files"].append(self._out_files[i])
            outputs["coverage"].append(self._coverage[i])

            for k in self._keys:
                outputs[k].append(getattr(self.inputs, k)[i])

        return outputs
