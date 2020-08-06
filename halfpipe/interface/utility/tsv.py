# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from pathlib import Path
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

from ...io import loadspreadsheet


class FillNAInputSpec(TraitedSpec):
    in_tsv = File(exists=True, desc="input tsv file")
    replace_with = traits.Float(default=0.0, usedefault=True)


class TsvOutputSpec(TraitedSpec):
    out_with_header = File(exists=True, desc="output tsv file")
    out_no_header = File(exists=True, desc="output tsv file")
    column_names = traits.List(
        traits.Str, desc="list of column names in order"
    )


class FillNA(SimpleInterface):
    """
    Remove NA values
    """

    input_spec = FillNAInputSpec
    output_spec = TsvOutputSpec

    def _run_interface(self, runtime):
        in_file = self.inputs.in_tsv

        if isdefined(in_file):
            replace_with = self.inputs.replace_with

            df = loadspreadsheet(in_file)

            non_finite_count = np.logical_not(np.isfinite(df.values)).sum()
            if non_finite_count > 0:
                logging.getLogger("halfpipe").warning(f"Replacing {non_finite_count:d} non-finite values with {replace_with:f} in file \"{in_file}\"")

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df.fillna(replace_with, inplace=True)
                self._results["out_no_header"] = Path.cwd() / "fillna_no_header.tsv"
                df.to_csv(
                    self._results["out_no_header"], sep="\t", index=False, na_rep="n/a", header=False
                )
            else:
                self._results["out_no_header"] = in_file
                self._results["column_names"] = list(df.columns)

        return runtime


class MergeColumnsInputSpec(DynamicTraitedSpec):
    row_index = traits.Either(traits.List(traits.Str), traits.Bool(), default=False, usedefault=True)


class MergeColumns(IOBase):
    """
    """

    input_spec = MergeColumnsInputSpec
    output_spec = TsvOutputSpec

    def __init__(self, numinputs=0, **inputs):
        super(MergeColumns, self).__init__(**inputs)
        self._numinputs = numinputs
        if numinputs >= 1:
            input_names = ["in%d" % (i + 1) for i in range(numinputs)]
            add_traits(self.inputs, input_names, trait_type=File)
            input_names = ["column_names%d" % (i + 1) for i in range(numinputs)]
            add_traits(self.inputs, input_names)
        else:
            input_names = []

    def _list_outputs(self):
        outputs = self._outputs().get()

        if self._numinputs < 1:
            return outputs

        out_df = None

        for i in range(self._numinputs):
            in_file = getattr(self.inputs, "in%d" % (i + 1))
            if not isdefined(in_file):
                continue
            in_df = loadspreadsheet(in_file)
            if in_df.size == 0:
                continue
            column_names = getattr(self.inputs, "column_names%d" % (i + 1))
            if isdefined(column_names):
                if not isinstance(column_names, (list, tuple)):
                    column_names = [column_names]
                in_df.columns = column_names
            if out_df is None:
                out_df = in_df
            else:
                out_df = pd.concat((out_df, in_df), axis=1)

        index = self.inputs.row_index is not False
        if isinstance(self.inputs.row_index, list):
            index = True
            out_df.index = self.inputs.row_index

        outputs["out_with_header"] = Path.cwd() / "merge_with_header.tsv"
        out_df.to_csv(
            outputs["out_with_header"], sep="\t", index=index, na_rep="n/a", header=True
        )
        outputs["out_no_header"] = Path.cwd() / "merge_no_header.tsv"
        out_df.to_csv(
            outputs["out_no_header"], sep="\t", index=False, na_rep="n/a", header=False
        )
        outputs["column_names"] = list(out_df.columns)

        return outputs


class SelectColumnsInputSpec(TraitedSpec):
    in_file = File(exists=True, desc="input tsv file")
    column_names = traits.List(
        traits.Str, desc="list of column names, can be regular expressions"
    )


class SelectColumns(SimpleInterface):
    """
    Select columns to make a design matrix
    """

    input_spec = SelectColumnsInputSpec
    output_spec = TsvOutputSpec

    def _run_interface(self, runtime):
        inputpath = self.inputs.in_file
        column_names = self.inputs.column_names

        filter = re.compile("^(" + "|".join(column_names) + ")$")
        dataframe = loadspreadsheet(inputpath)
        dataframe = dataframe[
            [
                column
                for column in dataframe.columns
                if filter.match(column) is not None and len(column_names) > 0
            ]
        ]
        self._results["out_with_header"] = Path.cwd() / "select_with_header.tsv"
        dataframe.to_csv(
            self._results["out_with_header"], sep="\t", index=False, na_rep="n/a", header=True
        )
        self._results["out_no_header"] = Path.cwd() / "select_no_header.tsv"
        dataframe.to_csv(
            self._results["out_no_header"], sep="\t", index=False, na_rep="n/a", header=False
        )
        self._results["column_names"] = list(dataframe.columns)

        return runtime
