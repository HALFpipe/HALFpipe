# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path

from nipype.interfaces.base import traits, TraitedSpec
from nipype.interfaces import fsl


class MultipleRegressDesignOutputSpec(TraitedSpec):
    design_mat = traits.Either(traits.File(exists=True, desc="design matrix file"), traits.Bool())
    design_con = traits.Either(
        traits.File(exists=True, desc="design t-contrast file"), traits.Bool()
    )
    design_fts = traits.Either(
        traits.File(exists=True, desc="design f-contrast file"), traits.Bool()
    )
    design_grp = traits.Either(traits.File(exists=True, desc="design group file"), traits.Bool())
    regs = traits.List(traits.Str())


class MultipleRegressDesign(fsl.MultipleRegressDesign):
    output_spec = MultipleRegressDesignOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        nfcons = sum([1 for con in self.inputs.contrasts if con[1] == "F"])
        for field in list(outputs.keys()):
            if ("fts" in field) and (nfcons == 0):
                outputs[field] = False
                continue
            outputs[field] = str(Path(os.getcwd()) / field.replace("_", "."))
        outputs["regs"] = sorted(self.inputs.regressors.keys())  # design matrix column names
        return outputs
