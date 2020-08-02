# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
import re

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File,
    DynamicTraitedSpec,
    isdefined,
)
from nipype.interfaces.io import add_traits, IOBase
import pandas as pd
import numpy as np

from ..utils import readtsv


def _merge_columns(in_list):
    out_array = None
    for idx, in_file in enumerate(in_list):
        in_array = readtsv(in_file)
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


class MergeColumnsOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output tsv file")


class MergeColumns(IOBase):
    """
    """

    input_spec = DynamicTraitedSpec
    output_spec = MergeColumnsOutputSpec

    def __init__(self, numinputs=0, **inputs):
        super(MergeColumns, self).__init__(**inputs)
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

        values = [getval(idx) for idx in range(self._numinputs) if isdefined(getval(idx))]

        out_file = None

        if len(values) > 0:
            out_file = _merge_columns(values)

        outputs["out_file"] = out_file
        return outputs


def _select_columns(column_names=None, inputpath=None, output_with_header=False):
    filter = re.compile("^(" + "|".join(column_names) + ")$")
    dataframe = pd.read_csv(inputpath, sep="\t")
    dataframe = dataframe[
        [
            column
            for column in dataframe.columns
            if filter.match(column) is not None and len(column_names) > 0
        ]
    ]
    outputpath = op.join(os.getcwd(), "selected_columns.tsv")
    dataframe.to_csv(
        outputpath, sep="\t", index=False, na_rep="n/a", header=output_with_header
    )
    return outputpath


class SelectColumnsInputSpec(TraitedSpec):
    in_file = File(exists=True, desc="input tsv file")
    column_names = traits.List(
        traits.Str, desc="list of column names, can be regular expressions"
    )
    output_with_header = traits.Bool(False, usedefault=True)


class SelectColumnsOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output tsv file")


class SelectColumns(SimpleInterface):
    """
    Select columns to make a design matrix
    """

    input_spec = SelectColumnsInputSpec
    output_spec = SelectColumnsOutputSpec

    def _run_interface(self, runtime):
        outputpath = _select_columns(
            column_names=self.inputs.column_names,
            inputpath=self.inputs.in_file,
            output_with_header=self.inputs.output_with_header,
        )
        self._results["out_file"] = outputpath

        return runtime
