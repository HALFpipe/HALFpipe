# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os.path import commonprefix
from pathlib import Path

import nibabel as nib
import numpy as np
from nilearn.image import new_img_like
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, isdefined, traits

from ...utils.image import nifti_dim

dimensions = ["x", "y", "z", "t"]


def _merge_fname(in_files):
    prefix = commonprefix([Path(f).name for f in in_files])
    if len(prefix) > 0:
        prefix += "_"

    fname = Path.cwd() / f"{prefix}merge.nii.gz"

    count = 1
    while fname.exists():
        fname = Path.cwd() / f"{prefix}{count}_merge.nii.gz"
        count += 1

    return fname


def _merge(in_files, dimension):
    in_imgs = [nib.load(f) for f in in_files]

    idim = dimensions.index(dimension)

    sizes = [nifti_dim(in_img, idim) for in_img in in_imgs]

    outshape = list(in_imgs[0].shape)
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

    outimg = new_img_like(in_imgs[0], outarr, copy_header=True)

    merged_file = _merge_fname(in_files)
    nib.save(outimg, merged_file)

    return merged_file


def _merge_mask(in_files):
    in_imgs = [nib.load(in_file) for in_file in in_files]

    outshape = in_imgs[0].shape
    assert all(in_img.shape == outshape for in_img in in_imgs), "Mask shape mismatch"

    in_data = [np.asanyarray(in_img.dataobj).astype(bool) for in_img in in_imgs]
    outarr = np.logical_and.reduce(in_data)

    outimg = new_img_like(in_imgs[0], outarr, copy_header=True)

    merged_file = _merge_fname(in_files)
    nib.save(outimg, merged_file)

    return merged_file


class MergeInputSpec(TraitedSpec):
    in_files = traits.List(
        File(desc="Image file(s) to resample", exists=True), mandatory=True
    )
    dimension = traits.Enum(
        *dimensions, desc="dimension along which to merge", mandatory=True
    )


class MergeOutputSpec(TraitedSpec):
    merged_file = traits.Either(File(), traits.Bool())


class Merge(SimpleInterface):
    input_spec = MergeInputSpec
    output_spec = MergeOutputSpec

    def _run_interface(self, runtime):
        self._merged_file = None

        in_files = self.inputs.in_files

        if not isdefined(in_files) or len(in_files) == 0:
            self._results["merged_file"] = False
            return runtime

        merged_file = _merge(in_files, self.inputs.dimension)

        self._results["merged_file"] = str(merged_file)

        return runtime


class MergeMaskInputSpec(TraitedSpec):
    in_files = traits.List(
        File(desc="Image file(s) to resample", exists=True), mandatory=True
    )


class MergeMask(SimpleInterface):
    input_spec = MergeMaskInputSpec
    output_spec = MergeOutputSpec

    def _run_interface(self, runtime):
        self._merged_file = None

        in_files = self.inputs.in_files

        if not isdefined(in_files) or len(in_files) == 0:
            self._results["merged_file"] = False
            return runtime

        merged_file = _merge_mask(in_files)

        self._results["merged_file"] = str(merged_file)

        return runtime
