# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
from nipype.interfaces.base import (
    DynamicTraitedSpec,
    File,
    SimpleInterface,
    TraitedSpec,
    isdefined,
    traits,
)
from nipype.interfaces.io import IOBase, add_traits

from ...ingest.spreadsheet import read_spreadsheet
from ...utils.ops import ravel


class FillNAInputSpec(TraitedSpec):
    in_tsv = File(exists=True, desc="input tsv file")
    replace_with = traits.Float(default=0.0, usedefault=True)


class TsvOutputSpec(TraitedSpec):
    out_with_header = File(exists=True, desc="output tsv file with a header")
    out_no_header = File(exists=True, desc="output tsv file without header")
    column_names = traits.List(traits.Str, desc="list of column names in order")


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

            df = read_spreadsheet(in_file)

            non_finite_count = np.logical_not(np.isfinite(df.values)).sum()
            if non_finite_count > 0:
                logging.getLogger("halfpipe").warning(
                    f'Replacing {non_finite_count:d} non-finite values with {replace_with:f} in file "{in_file}"'
                )

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df.fillna(replace_with, inplace=True)

            self._results["out_no_header"] = Path.cwd() / "fillna_no_header.tsv"
            df.to_csv(
                self._results["out_no_header"],
                sep="\t",
                index=False,
                na_rep="n/a",
                header=False,
            )

            self._results["column_names"] = list(map(str, df.columns))
        return runtime


class MergeColumnsInputSpec(DynamicTraitedSpec):
    row_index = traits.Any(default=False, usedefault=True)


class MergeColumns(IOBase):
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
        output_spec = self._outputs()
        assert output_spec is not None
        outputs = output_spec.get()

        row_index = self.inputs.row_index
        use_index = isdefined(row_index) and row_index is True

        if self._numinputs < 1:
            return outputs

        data_frames: list[pd.DataFrame] = list()

        for i in range(self._numinputs):
            file_paths = getattr(self.inputs, "in%d" % (i + 1))
            column_names = getattr(self.inputs, "column_names%d" % (i + 1))

            if not isdefined(file_paths):
                continue

            if isinstance(file_paths, str):
                file_paths = [file_paths]

            file_paths = ravel(file_paths)

            for file_path in file_paths:
                data_frame = read_spreadsheet(file_path)

                if data_frame.size == 0:
                    continue

                if isdefined(column_names):
                    if not isinstance(column_names, (list, tuple)):
                        column_names = [column_names]
                    data_frame.set_axis(column_names, axis="columns", inplace=True)

                data_frames.append(data_frame)

        if len(data_frames) == 0:
            data_frame = pd.DataFrame()
        else:
            data_frame = pd.concat(data_frames, axis=1)

        if isinstance(row_index, list):
            if len(row_index) == len(data_frame.index):
                use_index = True
                data_frame.index = self.inputs.row_index

        out_with_header = Path.cwd() / "merge_with_header.tsv"
        out_no_header = Path.cwd() / "merge_no_header.tsv"

        kwargs = dict(sep="\t", na_rep="n/a")
        data_frame.to_csv(out_with_header, index=use_index, header=True, **kwargs)
        data_frame.to_csv(out_no_header, index=False, header=False, **kwargs)

        outputs["out_with_header"] = out_with_header
        outputs["out_no_header"] = out_no_header
        outputs["column_names"] = list(map(str, data_frame.columns))

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
        dataframe = read_spreadsheet(inputpath)
        dataframe = dataframe[
            [
                column
                for column in dataframe.columns
                if filter.match(column) is not None and len(column_names) > 0
            ]
        ]
        self._results["out_with_header"] = Path.cwd() / "select_with_header.tsv"
        dataframe.to_csv(
            self._results["out_with_header"],
            sep="\t",
            index=False,
            na_rep="n/a",
            header=True,
        )
        self._results["out_no_header"] = Path.cwd() / "select_no_header.tsv"
        dataframe.to_csv(
            self._results["out_no_header"],
            sep="\t",
            index=False,
            na_rep="n/a",
            header=False,
        )
        self._results["column_names"] = list(map(str, dataframe.columns))

        return runtime
