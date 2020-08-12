# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import numpy as np
import pandas as pd

from nipype.interfaces.base import traits, TraitedSpec, SimpleInterface, File, isdefined

from ...utils import splitext
from ...io import loadmatrix, loadspreadsheet


class ToAFNIInputSpec(TraitedSpec):
    in_file = File(exists=True, mandatory=True)


class ToAFNIOutputSpec(TraitedSpec):
    out_file = File(exists=True)
    metadata = traits.Any()


class ToAFNI(SimpleInterface):
    """ convert to afni 1d format if necessary """

    input_spec = ToAFNIInputSpec
    output_spec = ToAFNIOutputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_file
        stem, ext = splitext(in_file)

        if ext in [".nii", ".nii.gz"]:
            self._results["out_file"] = in_file
            self._results["metadata"] = None

        else:
            in_df = loadspreadsheet(in_file)

            out_file = Path.cwd() / f"{stem}.1D"

            array = in_df.values.T
            np.nan_to_num(array, copy=False)
            np.savetxt(out_file, array, delimiter=" ")

            self._results["out_file"] = out_file
            self._results["metadata"] = list(in_df.columns)

        return runtime


class FromAFNIInputSpec(TraitedSpec):
    in_file = File(exists=True)
    metadata = traits.Any()


class FromAFNIOutputSpec(TraitedSpec):
    out_file = File(exists=True)


class FromAFNI(SimpleInterface):
    """ convert from afni 1d format if necessary """

    input_spec = FromAFNIInputSpec
    output_spec = FromAFNIOutputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_file
        stem, ext = splitext(in_file)

        if ext in [".nii", ".nii.gz"]:
            self._results["out_file"] = in_file

        else:
            in_array = loadmatrix(in_file).T

            column_names = None
            if isdefined(self.inputs.metadata):
                column_names = list(self.inputs.metadata)

            out_df = pd.DataFrame(data=in_array, columns=column_names)

            out_file = Path.cwd() / f"{stem}.tsv"
            out_df.to_csv(
                out_file, sep="\t", index=False, na_rep="n/a", header=True
            )

            self._results["out_file"] = out_file

        return runtime
