# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

import nibabel as nib

from nipype.interfaces.base import (
    TraitedSpec, BaseInterface, traits, File
)


class DofInputSpec(TraitedSpec):
    """ """
    in_file = File(exists=True,
                   mandatory=True,
                   desc="input file")
    out_file = File(
        "dof",
        usedefault=True,
        desc="output file name")
    num_regressors = traits.Range(
        low=1,
        mandatory=True,
        desc="number of regressors")


class DofOutputSpec(TraitedSpec):
    """ """
    out_file = File(exists=True)


class Dof(BaseInterface):
    """ simple interface to write a dof text file """
    input_spec = DofInputSpec
    output_spec = DofOutputSpec

    def _run_interface(self, runtime):
        """

        :param runtime: the runtime

        """
        im = nib.load(self.inputs.in_file)
        dof = im.shape[3] - self.inputs.num_regressors
        with open(op.abspath(self.inputs.out_file), "w") as f:
            f.write("%i" % dof)
            f.write("\n")
        return runtime

    def _list_outputs(self):
        """ """
        outputs = self._outputs().get()
        outputs["out_file"] = op.abspath(self.inputs.out_file)
        return outputs
