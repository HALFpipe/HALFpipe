# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from os import path as op

import numpy as np
import nibabel as nib

from nilearn.image import new_img_like

from nipype.interfaces.base import (
    SimpleInterface,
    DynamicTraitedSpec,
    traits,
    isdefined,
    File,
    InputMultiPath,
    OutputMultiPath,
    add_traits
)


class MaskCoverageInputSpec(DynamicTraitedSpec):
    in_files = InputMultiPath(File(exists=True), desc="Input files", mandatory=True)

    mask_file = File(desc="Mask file", exists=True, mandatory=True)

    min_mask_coverage = traits.Float(1.0)


class MaskCoverageOutputSpec(DynamicTraitedSpec):
    mask_file = OutputMultiPath(File(exists=True))
    coverage = traits.List(traits.Float)


class MaskCoverage(IOBase):
    input_spec = MaskCoverageInputSpec
    output_spec = MaskCoverageOutputSpec

    def __init__(self, keys=[], **inputs):
        super(MaskCoverage, self).__init__(**inputs)
        self._keys = keys

    def _add_output_traits(self, base):
        return add_traits(base, self._keys)

    def _run_interface(self, runtime):
        mask_img = nib.load(self.inputs.mask_file)
        mask = np.asanyarray(mask_img.dataobj).astype(np.bool)
        mask = np.squeeze(mask)

        mask_n_voxels = np.count_nonzero(mask)



        seed_img = nib.load(seed_file)
        seed = np.asanyarray(seed_img.dataobj).astype(np.bool)
        seed = np.squeeze(seed)

        unmasked_seed_n_voxels = np.count_nonzero(seed)

        seed = np.logical_and(seed, mask)

        masked_seed_n_voxels = np.count_nonzero(seed)

        coverage = float(masked_seed_n_voxels) / float(unmasked_seed_n_voxels)

        if coverage < min_seed_coverage:
            continue

        out_seed_names.append(seed_name)
        out_coverage.append(coverage)

        out_seed_file = Path.cwd() / Path(seed_file).name

        out_seed_img = new_img_like(seed_img, seed)
        nib.save(out_seed_img, out_seed_file)

        out_seed_files.append(out_seed_file)

    return out_seed_names, out_seed_files, out_coverage

        self._merged_file = None

        if not isdefined(self.inputs.in_files):
            self._results["merged_file"] = False
            return runtime

        in_imgs = [nib.load(in_file) for in_file in self.inputs.in_files]

        if len(in_imgs) == 0:
            self._results["merged_file"] = False
            return runtime

        outshape = first(in_imgs).shape
        assert all(in_img.shape == outshape for in_img in in_imgs)

        in_data = [np.asanyarray(in_img.dataobj).astype(np.bool) for in_img in in_imgs]
        outarr = np.logical_and.reduce(in_data)

        outimg = new_img_like(first(in_imgs), outarr)

        merged_file = op.abspath(f"merged.nii.gz")
        nib.save(outimg, merged_file)

        self._results["merged_file"] = merged_file

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        return outputs
