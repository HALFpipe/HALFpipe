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
    TraitedSpec,
    isdefined,
    traits
)

from ..io import loadspreadsheet
from ..utils import splitext, nvol


class TransformerInputSpec(TraitedSpec):
    in_file = traits.File(desc="File to filter", exists=True, mandatory=True)
    mask = traits.File(desc="mask to use for volumes", exists=True)


class TransformerOutputSpec(TraitedSpec):
    out_file = traits.File()


class Transformer(SimpleInterface):
    """
    Interface that takes any kind of array input and applies a function to it
    """
    input_spec = TransformerInputSpec
    output_spec = TransformerOutputSpec

    suffix = "transformed"

    def _transform(self, array):
        raise NotImplementedError()

    def _load(self, in_file):
        stem, ext = splitext(in_file)
        self.stem, self.ext = stem, ext

        self.mask = None
        if ext in [".nii", ".nii.gz"]:
            in_img = nib.load(in_file)
            self.in_img = in_img

            n = nvol(in_img)
            in_fdata = in_img.get_fdata(dtype=np.float64)
            array = in_fdata.reshape((-1, n))

            mask_file = self.inputs.mask
            if isdefined(mask_file):
                mask_img = nib.load(mask_file)
                assert nvol(mask_img) == 1
                assert np.allclose(mask_img.affine, in_img.affine)
                mask_fdata = mask_img.get_fdata(dtype=np.float64)
                mask_bin = np.logical_not(
                    np.logical_or(mask_fdata <= 0, np.isclose(mask_fdata, 0, atol=1e-2))
                )
                self.mask = mask_bin
                assert self.mask.size == array.shape[0]
                array = array[np.ravel(self.mask), :].T

        else:
            in_df = loadspreadsheet(in_file)
            self.in_df = in_df

            array = in_df.to_numpy().astype(np.float64)

        return array

    def _dump(self, array2):
        stem, ext = self.stem, self.ext

        out_file = op.abspath(f"{stem}_{self.suffix}{ext}")

        if ext in [".nii", ".nii.gz"]:
            in_img = self.in_img

            if self.mask is not None:
                m, n = array2.T.shape
                out_array = np.zeros((*in_img.shape[:3], n))
                out_array[self.mask, :] = array2.T
            else:
                out_array = array2.T.reshape((*in_img.shape[:3], -1))

            out_img = new_img_like(in_img, out_array)
            nib.save(out_img, out_file)

        else:
            in_df = self.in_df

            out_df = in_df
            np.copyto(out_df.values, array2)
            out_df.to_csv(
                out_file, sep="\t", index=False, na_rep="n/a", header=True
            )

        return out_file

    def _run_interface(self, runtime):
        self._merged_file = None

        in_file = self.inputs.in_file

        array = self._load(in_file)  # observations x variables

        array2 = self._transform(array)

        out_file = self._dump(array2)
        self._results["out_file"] = out_file

        return runtime
