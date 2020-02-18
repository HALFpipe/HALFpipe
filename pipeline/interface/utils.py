# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
import sys
import re

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File,
    DynamicTraitedSpec,
    isdefined
)
from nipype.interfaces.io import (
    add_traits,
    IOBase
)
import pandas as pd
import numpy as np


def _matrix_to_tsv(matrix=None):
    outputpath = op.join(os.getcwd(), "merged_columns.tsv")
    np.savetxt(outputpath, matrix, delimiter="\t")
    return outputpath


class MatrixToTSVInputSpec(TraitedSpec):
    matrix = traits.Array(desc="matrix")


class MatrixToTSVOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output file")


class MatrixToTSV(SimpleInterface):
    """
    Select columns to make a design matrix
    """

    input_spec = MatrixToTSVInputSpec
    output_spec = MatrixToTSVOutputSpec

    def _run_interface(self, runtime):
        outputpath = _matrix_to_tsv(
            matrix=self.inputs.matrix,
        )
        self._results["out_file"] = outputpath

        return runtime


def _robust_read_columns(in_file):
    try:
        in_array = np.genfromtxt(
            in_file,
            missing_values="NaN,n/a,NA")
        return in_array
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(
            in_file, skip_header=1,
            missing_values="NaN,n/a,NA")
        return in_array
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(
            in_file, delimiter=",",
            missing_values="NaN,n/a,NA")
        return in_array
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(
            in_file, delimiter=",", skip_header=1,
            missing_values="NaN,n/a,NA")
        return in_array
    except ValueError as e:
        sys.stdout.write("Could not load file {}".format(in_file))
        raise e


def _merge_columns(in_list):
    out_array = None
    for idx, in_file in enumerate(in_list):
        in_array = _robust_read_columns(in_file)
        if in_array.ndim == 1:  # single column file
            in_array = in_array.reshape((-1, 1))
        if in_array.size > 0:
            if out_array is None:
                out_array = in_array
            else:
                out_array = np.hstack((out_array, in_array))
    out_array = np.squeeze(out_array)
    outputpath = op.join(os.getcwd(), "merged_columns.tsv")
    np.savetxt(outputpath, out_array, delimiter="\t")
    return outputpath


class MergeColumnsTSVInputSpec(DynamicTraitedSpec):
    pass


class MergeColumnsTSVOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output tsv file")


class MergeColumnsTSV(IOBase):
    """
    Select columns to make a design matrix
    """

    input_spec = MergeColumnsTSVInputSpec
    output_spec = MergeColumnsTSVOutputSpec

    def __init__(self, numinputs=0, **inputs):
        super(MergeColumnsTSV, self).__init__(**inputs)
        self._numinputs = numinputs
        if numinputs >= 1:
            input_names = ["in%d" % (i + 1) for i in range(numinputs)]
            add_traits(self.inputs, input_names, trait_type=File)
        else:
            input_names = []

    def _list_outputs(self):
        outputs = self._outputs().get()

        if self._numinputs < 1:
            return outputs

        def getval(idx):
            return getattr(self.inputs, "in%d" % (idx + 1))

        values = [
            getval(idx) for idx in range(self._numinputs)
            if isdefined(getval(idx))
        ]

        out_file = None

        if len(values) > 0:
            out_file = _merge_columns(
                values
            )

        outputs["out_file"] = out_file
        return outputs


def _select_columns(column_names=None, inputpath=None,
                    header=False):
    filter = re.compile("^(" + "|".join(column_names) + ")$")
    dataframe = pd.read_csv(inputpath, sep="\t")
    dataframe = dataframe[[
        column for column in dataframe.columns
        if filter.match(column) is not None and
        len(column_names) > 0
    ]]
    outputpath = op.join(os.getcwd(), "selected_columns.tsv")
    dataframe.to_csv(outputpath, sep="\t", index=False,
                     na_rep="n/a",
                     header=header)
    return outputpath


class SelectColumnsTSVInputSpec(TraitedSpec):
    in_file = File(exists=True, desc="input tsv file")
    column_names = traits.List(
        traits.Str, desc="list of column names, can be regular expressions")
    header = traits.Bool(False, usedefault=True)


class SelectColumnsTSVOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output tsv file")


class SelectColumnsTSV(SimpleInterface):
    """
    Select columns to make a design matrix
    """

    input_spec = SelectColumnsTSVInputSpec
    output_spec = SelectColumnsTSVOutputSpec

    def _run_interface(self, runtime):
        outputpath = _select_columns(
            column_names=self.inputs.column_names,
            inputpath=self.inputs.in_file,
            header=self.inputs.header
        )
        self._results["out_file"] = outputpath

        return runtime
