# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import List

from calamities import (
    TextView,
    SpacerView,
    NumberInputView,
    SingleChoiceInputView,
    FileInputView,
)

import numpy as np
import pandas as pd
from inflection import humanize
from marshmallow import fields

from .step import Step
from ..io.metadata import direction_code_str, slice_timing_str
from ..model import space_codes, slice_order_strs


def _get_field(schema, key):
    if isinstance(schema, type):
        instance = schema()
    else:
        instance = schema
    if "metadata" in instance.fields:
        return _get_field(instance.fields["metadata"].nested, key)
    return instance.fields.get(key)


def _get_unit(schema, key):
    field = _get_field(schema, key)
    if field is not None:
        return field.metadata.get("unit")


def display_str(x):
    if x == "MNI152NLin6Asym":
        return "MNI ICBM 152 non-linear 6th Generation Asymmetric (FSL)"
    elif x == "MNI152NLin2009cAsym":
        return "MNI ICBM 2009c Nonlinear Asymmetric"
    elif x == "slice_encoding_direction":
        return "slice acquisition direction"
    return humanize(x)


class ImportMetadataStep(Step):
    def __init__(self, app, filters, schema, key, suggestion, next_step_type, appendstr=""):
        super(ImportMetadataStep, self).__init__(app)

        self.schema = schema
        self.key = key
        self.field = _get_field(self.schema, self.key)
        self.appendstr = appendstr

        self.suggestion = suggestion

        self.filters = filters

        self.next_step_type = next_step_type

    def setup(self, ctx):
        humankey = display_str(self.key).lower()

        unit = _get_unit(self.schema, self.key)
        field = self.field

        assert isinstance(field, fields.List)

        header_str = f"Import {humankey} values{self.appendstr}"
        if unit is not None:
            header_str += f" in {unit}"
        header_str += " from a file"

        self._append_view(TextView(header_str))

        self.input_view = FileInputView()

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.result = self.input_view()
        if self.result is None:
            return False
        return True

    def next(self, ctx):
        if self.result is not None:
            filepath = self.result

            spreadsheet = pd.read_table(
                filepath,
                sep="\s+",
                header=None,
                names=["slice_times"],
                index_col=False,
                usecols=[0],
                dtype=float,
            )
            valuearray = np.ravel(spreadsheet.slice_times.values).astype(np.float64)
            valuelist: List = list(valuearray.tolist())

            value = self.field.deserialize(valuelist)

            if self.filters is None:
                specfileobjs = [ctx.spec.files[-1]]
            else:
                filepaths = ctx.database.get(**self.filters)
                specfileobjs = set(ctx.database.specfileobj(filepath) for filepath in filepaths)

            for specfileobj in specfileobjs:
                if not hasattr(specfileobj, "metadata"):
                    specfileobj.metadata = dict()
                specfileobj.metadata[self.key] = value

        return self.next_step_type(self.app)(ctx)


class SetMetadataStep(Step):
    def __init__(self, app, filters, schema, key, suggestion, next_step_type, appendstr=""):
        super(SetMetadataStep, self).__init__(app)

        self.schema = schema
        self.key = key
        self.field = _get_field(self.schema, self.key)
        self.appendstr = appendstr

        self.suggestion = suggestion

        self.filters = filters

        self.next_step_type = next_step_type

    def setup(self, ctx):
        humankey = display_str(self.key).lower()

        unit = _get_unit(self.schema, self.key)
        field = self.field

        header_str = f"Specify {humankey}{self.appendstr}"
        if unit is not None and self.key != "slice_timing":
            header_str += f" in {unit}"

        self._append_view(TextView(header_str))

        self.aliases = {}

        if field.validate is not None and hasattr(field.validate, "choices") or self.key == "slice_timing":
            choices = None
            display_choices = None

            if self.key == "slice_timing":
                choices = [*slice_order_strs, "import from file"]
                display_choices = [
                    "Sequential increasing (1, 2, ...)",
                    "Sequential decreasing (... 2, 1)",
                    "Alternating increasing even first (2, 4, ... 1, 3, ...)",
                    "Alternating increasing odd first (1, 3, ... 2, 4, ...)",
                    "Alternating decreasing even first (... 3, 1, ... 4, 2)",
                    "Alternating decreasing odd first (... 4, 2, ... 3, 1)",
                    "Import from file"
                ]

            if choices is None:
                choices = [*field.validate.choices]

            if set(space_codes).issubset(choices):
                choices = [*space_codes]
                if self.key == "slice_encoding_direction":
                    choices = list(reversed(choices))
                display_choices = [
                    display_str(direction_code_str(choice, None)) for choice in choices
                ]

            if display_choices is None:
                display_choices = [display_str(choice) for choice in choices]

            self.aliases = dict(zip(display_choices, choices))

            self.input_view = SingleChoiceInputView(display_choices, isVertical=True)

        elif isinstance(field, fields.Float):
            self.input_view = NumberInputView()

        else:
            raise ValueError(f'Unsupported metadata field "{field}"')

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.result = self.input_view()
        if self.result is None:
            return False
        return True

    def next(self, ctx):
        if self.result is not None:
            key = self.key
            value = self.result

            if value in self.aliases:
                value = self.aliases[value]

            if key == "slice_timing":
                if value == "import from file":
                    return ImportMetadataStep(
                        self.app,
                        self.filters,
                        self.schema,
                        self.key,
                        self.suggestion,
                        self.next_step_type,
                        appendstr=self.appendstr
                    )(ctx)
                else:  # a code was specified
                    key = "slice_timing_code"
                    self.field = _get_field(self.schema, key)

            value = self.field.deserialize(value)

            if self.filters is None:
                specfileobjs = [ctx.spec.files[-1]]
            else:
                filepaths = ctx.database.get(**self.filters)
                specfileobjs = set(ctx.database.specfileobj(filepath) for filepath in filepaths)

            for specfileobj in specfileobjs:
                if not hasattr(specfileobj, "metadata"):
                    specfileobj.metadata = dict()
                specfileobj.metadata[key] = value

        return self.next_step_type(self.app)(ctx)


class CheckMetadataStep(Step):
    schema = None

    key = None
    appendstr = ""

    filters = None

    next_step_type = None

    def _should_skip(self, ctx):
        return False

    def setup(self, ctx):
        self.is_first_run = True
        self.should_skip = self._should_skip(ctx)
        self.choice = None

        if self.should_skip:
            self.is_missing = True
            return

        humankey = display_str(self.key).lower()

        if self.filters is None:
            filepaths = [
                fileobj.path for fileobj in ctx.database.fromspecfileobj(ctx.spec.files[-1])
            ]
        else:
            filepaths = [*ctx.database.get(**self.filters)]

        ctx.database.fillmetadata(self.key, filepaths)

        vals = [ctx.database.metadata(filepath, self.key) for filepath in filepaths]
        self.suggestion = None

        if self.key == "phase_encoding_direction" or self.key == "slice_encoding_direction":
            for i, val in enumerate(vals):
                if val is not None:
                    vals[i] = direction_code_str(val, filepaths[i])

        elif self.key == "slice_timing":
            for i, val in enumerate(vals):
                if val is not None:
                    sts = slice_timing_str(val)
                    if sts == "unknown":
                        val = np.array(val)
                        sts = np.array2string(val, max_line_width=16384)
                    else:
                        sts = humanize(sts)
                    vals[i] = sts

        if any(val is None for val in vals):
            self.is_missing = True
            self._append_view(TextView(f"Missing {humankey} values"))

            vals = [val if val is not None else "missing" for val in vals]
        else:
            self.is_missing = False
            self._append_view(TextView(f"Check {humankey} values{self.appendstr}"))

        assert isinstance(vals, List)

        uniquevals, counts = np.unique(vals, return_counts=True)
        order = np.argsort(counts)

        column1 = []
        for i in range(min(10, len(order))):
            column1.append(f"{counts[i]} images")
        column1width = max(len(s) for s in column1)

        unit = _get_unit(self.schema, self.key)
        if unit is None:
            unit = ""

        if self.key == "slice_timing":
            unit = ""

        for i in range(min(10, len(order))):
            display = display_str(f"{uniquevals[i]}")
            if self.suggestion is None:
                self.suggestion = display
            tablerow = f" {column1[i]:>{column1width}} - {display}"
            if uniquevals[i] != "missing":
                tablerow = f"{tablerow} {unit}"
            self._append_view(TextView(tablerow))

        if len(order) > 10:
            self._append_view(TextView("..."))

        if self.is_missing is False:
            self._append_view(TextView("Proceed with these values?"))
            self.input_view = SingleChoiceInputView(["Yes", "No"], isVertical=False)
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
        if self.is_first_run or not self.is_missing:
            self.is_first_run = False
            if self.choice == "Yes" or self.should_skip:
                return self.next_step_type(self.app)(ctx)
            else:
                return SetMetadataStep(
                    self.app,
                    self.filters,
                    self.schema,
                    self.key,
                    self.suggestion,
                    self.next_step_type,
                    appendstr=self.appendstr
                )(ctx)
