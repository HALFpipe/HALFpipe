# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import numpy as np
import pandas as pd
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, isdefined

from ...utils.path import split_ext


class UnvestInputSpec(TraitedSpec):
    in_vest = File(exists=True, desc="input vest file")


class UnvestOutputSpec(TraitedSpec):
    out_no_header = File(exists=True, desc="output tsv file")


class Unvest(SimpleInterface):
    """
    Remove NA values
    """

    input_spec = UnvestInputSpec
    output_spec = UnvestOutputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_vest

        if isdefined(in_file):
            matrix = np.loadtxt(in_file, comments="/", ndmin=2)
            dataframe = pd.DataFrame(matrix)

            stem, _ = split_ext(in_file)
            self._results["out_no_header"] = Path.cwd() / f"{stem}_no_header.tsv"
            dataframe.to_csv(
                self._results["out_no_header"],
                sep="\t",
                index=False,
                na_rep="n/a",
                header=False,
            )

        return runtime
