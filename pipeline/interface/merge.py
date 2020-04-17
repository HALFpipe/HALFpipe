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
    BaseInterface,
    TraitedSpec,
    BaseInterfaceInputSpec,
    traits,
    isdefined,
)

from ..utils import niftidim, first

dimensions = ["x", "y", "z", "t"]


class SafeMergeInputSpec(BaseInterfaceInputSpec):
    in_files = traits.List(
        traits.File(desc="Image file(s) to resample", exists=True), mandatory=True
    )
    dimension = traits.Enum(*dimensions, desc="dimension along which to merge", mandatory=True)


class SafeMergeOutputSpec(TraitedSpec):
    merged_file = traits.File()


class SafeMerge(BaseInterface):
    input_spec = SafeMergeInputSpec
    output_spec = SafeMergeOutputSpec

    def _run_interface(self, runtime):
        self._merged_file = None

        if not isdefined(self.inputs.in_files):
            return runtime

        in_imgs = [nib.load(in_file) for in_file in self.inputs.in_files]
        idim = dimensions.index(self.inputs.dimension)

        sizes = [niftidim(in_img, idim) for in_img in in_imgs]

        outshape = list(first(in_imgs).shape)
        while len(outshape) < idim + 1:
            outshape.append(1)

        outshape[idim] = sum(sizes)

        movd_shape = [outshape[idim], *outshape[:idim], *outshape[idim + 1 :]]
        movd_outarr = np.zeros(movd_shape, dtype=np.float64)

        i = 0
        for in_img, size in zip(in_imgs, sizes):
            in_data = in_img.get_fdata()
            while len(in_data.shape) < idim + 1:
                in_data = np.expand_dims(in_data, len(in_data.shape))
            movd_outarr[i : i + size] = np.moveaxis(in_data, idim, 0)
            i += size

        outarr = np.moveaxis(movd_outarr, 0, idim)

        outimg = new_img_like(first(in_imgs), outarr)

        self._out_file = op.abspath(f"merged.nii.gz")
        nib.save(outimg, self._out_file)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if self._out_file is not None:
            outputs["out_file"] = self._out_file
        return outputs


class SafeMaskMergeInputSpec(BaseInterfaceInputSpec):
    in_files = traits.List(
        traits.File(desc="Image file(s) to resample", exists=True), mandatory=True
    )


class SafeMaskMergeOutputSpec(TraitedSpec):
    merged_file = traits.File()


class SafeMaskMerge(BaseInterface):
    input_spec = SafeMaskMergeInputSpec
    output_spec = SafeMaskMergeOutputSpec

    def _run_interface(self, runtime):
        self._merged_file = None

        if not isdefined(self.inputs.in_files):
            return runtime

        in_imgs = [nib.load(in_file) for in_file in self.inputs.in_files]

        outshape = first(in_imgs).shape
        assert all(in_img.shape == outshape for in_img in in_imgs)

        in_data = [np.asanyarray(in_img.dataobj).astype(np.bool) for in_img in in_imgs]
        outarr = np.logical_and.reduce(in_data)

        outimg = new_img_like(first(in_imgs), outarr)

        self._out_file = op.abspath(f"merged.nii.gz")
        nib.save(outimg, self._out_file)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if self._out_file is not None:
            outputs["out_file"] = self._out_file
        return outputs
