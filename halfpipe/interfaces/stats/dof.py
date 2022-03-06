# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

import nibabel as nib
import numpy as np
from nilearn.image import new_img_like
from nipype.interfaces.base import BaseInterface, File, TraitedSpec, isdefined, traits

from ...utils.image import nvol
from ...utils.matrix import ncol
from ...utils.ops import first_str


class MakeDofVolumeInputSpec(TraitedSpec):
    dof_file = File(desc="", exists=True)
    copes = traits.Either(traits.List(File(exists=True)), File(exists=True))

    bold_file = File(exists=True, desc="input file")
    num_regressors = traits.Range(low=1, desc="number of regressors")
    design = File(desc="", exists=True)


class MakeDofVolumeOutputSpec(TraitedSpec):
    out_file = File(exists=True)


class MakeDofVolume(BaseInterface):
    input_spec = MakeDofVolumeInputSpec
    output_spec = MakeDofVolumeOutputSpec

    def _run_interface(self, runtime):
        self._out_file = None

        dof = None
        ref_img = None

        if isdefined(self.inputs.dof_file):
            with open(self.inputs.dof_file) as file:
                dof = float(file.read())

        if isdefined(self.inputs.bold_file):
            ref_img = nib.load(self.inputs.bold_file)
            if isdefined(self.inputs.num_regressors):
                dof = float(nvol(ref_img) - self.inputs.num_regressors)
            elif isdefined(self.inputs.design):
                dof = float(nvol(ref_img) - ncol(self.inputs.design))

        if isdefined(self.inputs.copes):
            ref_img = nib.load(first_str(self.inputs.copes))

        if dof is None:
            return runtime

        if ref_img is None:
            return runtime

        outshape = ref_img.shape[:3]
        outarr = np.full(outshape, dof)

        outimg = new_img_like(ref_img, outarr, copy_header=True)
        assert isinstance(outimg.header, nib.Nifti1Header)
        outimg.header.set_data_dtype(np.float64)

        self._out_file = op.abspath("dof_file.nii.gz")
        nib.save(outimg, self._out_file)

        return runtime

    def _list_outputs(self):
        output_spec = self._outputs()
        assert output_spec is not None
        outputs = output_spec.get()

        if self._out_file is not None:
            outputs["out_file"] = self._out_file

        return outputs
