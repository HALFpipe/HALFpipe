# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File
)
import pandas as pd


def _select_columns(column_names=None, inputpath=None,
                    header=False):
    dataframe = pd.read_csv(inputpath, sep="\t")
    dataframe = dataframe[[column for column in dataframe.columns
                           if column in column_names]]
    outputpath = op.join(os.getcwd(), "selected_columns.tsv")
    dataframe.to_csv(outputpath, sep="\t", index=False,
                     na_rep="n/a",
                     header=header)
    return outputpath


class SelectColumnsInputSpec(TraitedSpec):
    input = File(exists=True, desc="input tsv file")
    column_names = traits.List(traits.Str, desc="list of column names")
    header = traits.Bool(False, usedefault=True)


class SelectColumnsOutputSpec(TraitedSpec):
    out = File(exists=True, desc="output tsv file")


class SelectColumns(SimpleInterface):
    """
    Select columns to make a design matrix
    """

    input_spec = SelectColumnsInputSpec
    output_spec = SelectColumnsOutputSpec

    def _run_interface(self, runtime):
        outputpath = _select_columns(
            column_names=self.inputs.column_names,
            inputpath=self.inputs.input,
            header=self.inputs.header
        )
        self._results["out"] = outputpath

        return runtime
