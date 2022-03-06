# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import numpy as np
import pandas as pd
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, isdefined, traits

from ...ingest.spreadsheet import read_spreadsheet
from ...utils.path import split_ext


class ToAFNIInputSpec(TraitedSpec):
    in_file = File(exists=True, mandatory=True)


class ToAFNIOutputSpec(TraitedSpec):
    out_file = File(exists=True)
    metadata = traits.Any()


class ToAFNI(SimpleInterface):
    """convert to afni 1d format if necessary"""

    input_spec = ToAFNIInputSpec
    output_spec = ToAFNIOutputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_file
        stem, ext = split_ext(in_file)

        if ext in [".nii", ".nii.gz"]:
            self._results["out_file"] = in_file
            self._results["metadata"] = None

        else:
            data_frame = read_spreadsheet(in_file)

            out_file = Path.cwd() / f"{stem}.1D"

            array = data_frame.values.transpose()
            array = np.nan_to_num(array, copy=False)
            np.savetxt(out_file, array, delimiter=" ")

            self._results["out_file"] = out_file
            self._results["metadata"] = list(data_frame.columns)

        return runtime


class FromAFNIInputSpec(TraitedSpec):
    in_file = File(exists=True)
    metadata = traits.Any()


class FromAFNIOutputSpec(TraitedSpec):
    out_file = File(exists=True)


class FromAFNI(SimpleInterface):
    """convert from afni 1d format if necessary"""

    input_spec = FromAFNIInputSpec
    output_spec = FromAFNIOutputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_file
        stem, ext = split_ext(in_file)

        if ext in [".nii", ".nii.gz"]:
            self._results["out_file"] = in_file

        else:
            in_array = read_spreadsheet(in_file).values.transpose()

            header = False
            column_names = None
            if isdefined(self.inputs.metadata):
                header = True
                column_names = list(self.inputs.metadata)

            out_df = pd.DataFrame(data=in_array, columns=column_names)

            out_file = Path.cwd() / f"{stem}.tsv"
            out_df.to_csv(out_file, sep="\t", index=False, na_rep="n/a", header=header)

            self._results["out_file"] = out_file

        return runtime
