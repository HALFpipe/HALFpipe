# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""


import logging

import pandas as pd

from ...ingest.spreadsheet import read_spreadsheet
from ...model import SpreadsheetFileSchema, VariableSchema
from ..components import (
    FileInputView,
    MultiSingleChoiceInputView,
    SingleChoiceInputView,
    SpacerView,
    TextElement,
    TextView,
)
from ..step import Step
from .filter import SubjectGroupFilterStep
from .utils import format_column

next_step_type = SubjectGroupFilterStep


class SpreadsheetColumnTypeStep(Step):
    def setup(self, ctx):
        self.is_first_run = True
        self.should_run = True
        self.choice = None

        already_used = set(
            variable["name"]
            for variable in ctx.spec.files[-1].metadata["variables"]
            if variable["type"] == "id"
        )  # omit id column

        self.df = read_spreadsheet(ctx.spec.files[-1].path)

        if all(column in already_used for column in self.df):
            self.should_run = False

        if self.should_run:
            self._append_view(TextView("Specify the column data types"))

            columns = [column for column in self.df if column not in already_used]
            options = [format_column(column) for column in columns]

            self.varname_by_str = dict(zip(options, columns))

            values = ["Continuous", "Categorical"]

            self.input_view = MultiSingleChoiceInputView(options, values)

            suggestions = {
                column: 1 if self.df[column].dtype == object else 0
                for column in columns
            }

            self.input_view.selectedIndices = [
                suggestions[column] for column in columns
            ]

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if not self.should_run:
            return self.is_first_run
        else:
            self.choice = self.input_view()
            if self.choice is None:
                return False
            return True

    def next(self, ctx):
        if self.choice is not None:
            for variable_str, value in self.choice.items():
                varname = self.varname_by_str[variable_str]
                vartype = value.lower()

                vardict = {"type": vartype, "name": varname}

                if vartype == "categorical":
                    levels = self.df[varname]
                    levels = levels[pd.notnull(levels)]
                    levels = levels.astype(str).unique().tolist()
                    vardict["levels"] = levels

                var = VariableSchema().load(vardict)
                ctx.spec.files[-1].metadata["variables"].append(var)

        ctx.database.put(
            ctx.spec.files[-1]
        )  # we've got all tags, so we can add the fileobj to the index

        if self.should_run or self.is_first_run:
            self.is_first_run = False
            return next_step_type(self.app)(ctx)


class SpreadsheetIdColumnStep(Step):
    def setup(self, ctx):
        self.is_first_run = True
        self.should_run = True
        self.choice = None

        if (
            not hasattr(ctx.spec.files[-1], "metadata")
            or ctx.spec.files[-1].metadata is None
        ):
            ctx.spec.files[-1].metadata = dict()

        if ctx.spec.files[-1].metadata.get("variables") is None:
            ctx.spec.files[-1].metadata["variables"] = []

        if any(
            variable["type"] == "id"
            for variable in ctx.spec.files[-1].metadata["variables"]
        ):
            self.should_run = False

        if self.should_run:
            self._append_view(TextView("Specify the column containing subject names"))

            already_used = set(
                v["name"] for v in ctx.spec.files[-1].metadata["variables"]
            )

            df = read_spreadsheet(ctx.spec.files[-1].path)
            columns = [column for column in df if column not in already_used]
            options = [format_column(column) for column in columns]

            self.varname_by_str = dict(zip(options, columns))

            self.input_view = SingleChoiceInputView(options, isVertical=True)

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if not self.should_run:
            return self.is_first_run
        else:
            self.choice = self.input_view()
            if self.choice is None:
                return False
            return True

    def next(self, ctx):
        if self.choice is not None:
            varname = self.varname_by_str[self.choice]
            var = VariableSchema().load({"type": "id", "name": varname})
            ctx.spec.files[-1].metadata["variables"].append(var)

        if self.should_run or self.is_first_run:
            self.is_first_run = False
            return SpreadsheetColumnTypeStep(self.app)(ctx)


class AddSpreadsheetStep(Step):
    def _messagefun(self):
        return self.message

    def setup(self, ctx):
        self.filepath = None
        self.message = None

        self._append_view(
            TextView("Specify the path of the covariates/group data spreadsheet file")
        )

        self.input_view = FileInputView(messagefun=self._messagefun)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            self.filepath = self.input_view()
            if self.filepath is None:  # was cancelled
                return False

            try:
                read_spreadsheet(self.filepath)
                return True
            except Exception as e:
                logging.getLogger("halfpipe.ui").exception("Exception: %s", e)
                error_color = self.app.layout.color.red
                self.message = TextElement(str(e), color=error_color)

    def next(self, ctx):
        ctx.spec.models[-1].spreadsheet = self.filepath

        exists_in_files = self.filepath in ctx.database.get(datatype="spreadsheet")

        if exists_in_files:
            return next_step_type(self.app)(ctx)
        else:
            ctx.spec.files.append(
                SpreadsheetFileSchema().load(
                    {"datatype": "spreadsheet", "path": self.filepath}
                )
            )
            return SpreadsheetIdColumnStep(self.app)(ctx)


class SpreadsheetSelectStep(Step):
    def setup(self, ctx):
        self.choice = None
        self.is_first_run = True

        filepaths = ctx.database.get(datatype="spreadsheet")

        self.is_missing = True

        self.choice = None
        if filepaths is not None and len(filepaths) > 0:
            self.is_missing = False

            self._append_view(
                TextView("Select the covariates/group data spreadsheet file")
            )

            self.add_file_str = "Add spreadsheet file"

            dsp_values = [f'"{value}"' for value in filepaths]
            dsp_values = [*dsp_values, self.add_file_str]

            self.filepath_by_str = dict(zip(dsp_values, filepaths))

            self.input_view = SingleChoiceInputView(dsp_values, isVertical=True)

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if self.is_missing:
            return self.is_first_run
        else:
            self.choice = self.input_view()
            if self.choice is None:
                return False
            return True

    def next(self, ctx):
        if self.choice is not None:
            if self.choice in self.filepath_by_str:
                ctx.spec.models[-1].spreadsheet = self.filepath_by_str[self.choice]

        if (self.is_first_run and self.is_missing) or (
            not self.is_missing and self.choice == self.add_file_str
        ):
            self.is_first_run = False
            return AddSpreadsheetStep(self.app)(ctx)

        elif self.is_first_run or not self.is_missing:
            self.is_first_run = False
            return next_step_type(self.app)(ctx)


SpreadsheetStep = SpreadsheetSelectStep
