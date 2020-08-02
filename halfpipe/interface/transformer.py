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
    traits
)

from ..io import loadspreadsheet
from ..utils import splitext, nvol


class TransformerInputSpec(TraitedSpec):
    in_file = traits.File(desc="File to filter", exists=True, mandatory=True)


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

        if ext in [".nii", ".nii.gz"]:
            in_img = nib.load(in_file)
            self.in_img = in_img

            n = nvol(in_img)
            in_fdata = in_img.get_fdata(dtype=np.float64)
            array = in_fdata.reshape((-1, n))

        else:
            in_df = loadspreadsheet(in_file)
            self.in_df = in_df

            array = in_df.to_numpy().astype(np.float64)

        return array

    def _dump(self, array2):
        stem, ext = self.stem, self.ext

        out_file = op.abspath(f"{stem}_{self.suffix}{ext}")
        self._results["out_file"] = out_file

        if ext in [".nii", ".nii.gz"]:
            in_img = self.in_img

            out_img = new_img_like(in_img, array2.reshape(in_img.shape))
            nib.save(out_img, out_file)

        else:
            in_df = self.in_df

            out_df = in_df
            out_df.values = array2
            out_df.to_csv(
                out_file, sep="\t", index=False, na_rep="n/a", header=True
            )

    def _run_interface(self, runtime):
        self._merged_file = None

        in_file = self.inputs.in_file

        array = self._load(in_file)

        array2 = self._transform(array)

        self._dump(array2)

        return runtime
