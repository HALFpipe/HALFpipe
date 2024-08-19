# -*- coding: utf-8 -*-
from __future__ import annotations

from itertools import product
from operator import attrgetter
from typing import ClassVar, Dict, Iterable, Optional, Type

import numpy as np
from inflection import humanize
from marshmallow import Schema, fields

from ...ingest.metadata.direction import canonicalize_direction_code, direction_code_str
from ...ingest.metadata.niftiheader import NiftiheaderLoader
from ...ingest.metadata.slicetiming import slice_timing_str
from ...ingest.spreadsheet import read_spreadsheet
from ...model.file.base import File
from ...model.file.fmap import (
    PhaseDiffFmapFileSchema,
    PhaseFmapFileSchema,
)
from ...model.file.func import (
    BoldFileSchema,
)
from ...model.metadata import slice_order_strs, space_codes
from ...model.tags import entities, entity_longnames

# from ..logging import logger
from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.selection_modal import SelectionModal
from ..utils.set_value_modal import SetValueModal
from .multichoice_radioset import MultipleRadioSetModal


def display_str(x):
    if x == "MNI152NLin6Asym":
        return "MNI ICBM 152 non-linear 6th Generation Asymmetric (FSL)"
    elif x == "MNI152NLin2009cAsym":
        return "MNI ICBM 2009c Nonlinear Asymmetric"
    elif x == "slice_encoding_direction":
        return "slice acquisition direction"
    return humanize(x)


##################### CheckMetadataSteps


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


# TODO ASAP
class SliceTimingFileStep:
    key = "slice_timing"

    def _messagefun(self):
        return self.message

    def __init__(self, app, filters, schema, suggestion, appendstr=""):
        #   super(SliceTimingFileStep, self).__init__(app)
        self.app = app
        self.schema = schema
        self.field = _get_field(self.schema, self.key)
        self.appendstr = appendstr

        self.suggestion = suggestion
        self.message = None

        self.filters = filters

        #  self.next_step_type = next_step_type
        self._append_view = []
        self.input_view: list = []

        # def setup(self, ctx):
        humankey = display_str(self.key).lower()

        unit = _get_unit(self.schema, self.key)

        if self.filters is None:
            specfileobj = ctx.spec.files[-1]
            self.specfileobjs: Iterable[File] = [specfileobj]

            self.filepaths = [fileobj.path for fileobj in ctx.database.fromspecfileobj(specfileobj)]
        else:
            self.filepaths = list(ctx.database.get(**self.filters))
            self.specfileobjs = set(ctx.database.specfileobj(filepath) for filepath in self.filepaths)

        for field in ["slice_encoding_direction", "repetition_time"]:
            assert ctx.database.fillmetadata(field, self.filepaths) is True  # should have already been done, but can't hurt

        header_str = f"Import {humankey} values{self.appendstr}"
        if unit is not None:
            header_str += f" in {unit}"
        header_str += " from a file"

        self._append_view.append(header_str)

        # self.input_view = FileInputView(messagefun=self._messagefun)
        # self.input_view.append(messagefun=self._messagefun)

        # self._append_view.append(self.input_view)
        # self._append_view.append(SpacerView(1))

        # def run(self, ctx):
        # error_color = self.app.layout.color.red

        while True:
            self.result = self.input_view[0]

            if self.result is None:
                return False

            # validate

            filepath = self.result
            try:
                spreadsheet = read_spreadsheet(filepath)
                valuearray = np.ravel(spreadsheet.values).astype(np.float64)
                valuelist = list(valuearray.tolist())
                value = self.field.deserialize(valuelist)

                for filepath in self.filepaths:
                    slice_encoding_direction = ctx.database.metadata(filepath, "slice_encoding_direction")
                    slice_encoding_direction = canonicalize_direction_code(slice_encoding_direction, filepath)
                    slice_encoding_axis = ["i", "j", "k"].index(slice_encoding_direction[0])
                    repetition_time = ctx.database.metadata(filepath, "repetition_time")

                    header, _ = NiftiheaderLoader.load(filepath)
                    if header is not None:
                        n_slices = header.get_data_shape()[slice_encoding_axis]
                        if n_slices != len(value):
                            raise ValueError(
                                f"Slice timing from file has {len(value):d} " f"values, but scans have {n_slices:d} slices"
                            )

                    for i, time in enumerate(value):
                        if time > repetition_time:
                            raise ValueError(
                                f"Invalid time for slice {i+1:d}: "
                                f"{time:f} seconds is greater than "
                                f"repetition_time of images "
                                f"({repetition_time:f} seconds)"
                            )

            except Exception:
                # TODO: output this warning as modal
                #         logger.warning(f'Failed to read slice timing from "{filepath}"', exc_info=e)
                #  self.message = TextElement(str(e), color=error_color)
                continue  # try again for correct file

            return True

    def next(self):
        if self.result is not None:
            filepath = self.result

            for specfileobj in self.specfileobjs:
                if not hasattr(specfileobj, "metadata"):
                    specfileobj.metadata = dict()
                specfileobj.metadata["slice_timing_file"] = filepath

    #   return self.next_step_type(self.app)(ctx)


class SetMetadataStep:
    def __init__(
        self,
        filters,
        schema,
        key,
        suggestion,
        appendstr="",
        app=None,
        next_step_type=None,
        callback=None,
        callback_message=None,
        id_key="",
        sub_id_key=None,
    ):
        # super(SetMetadataStep, self).__init__(app)

        self.schema = schema
        self.key = key
        self.field = _get_field(self.schema, self.key)
        self.appendstr = appendstr

        self.suggestion = suggestion

        self.filters = filters
        self._append_view: list[str] = []
        self.input_view: list[str] = []
        self.app = app
        self.next_step_type = next_step_type
        self.callback = callback
        self.humankey = display_str(self.key)  # .lower()
        self.id_key = id_key
        self.sub_id_key = sub_id_key
        self.callback_message = callback_message if callback_message is not None else {self.humankey: []}
        if callback_message is not None:
            self.callback_message.update({self.humankey: []})

    def run(self):
        #  def setup(self, _):

        unit = _get_unit(self.schema, self.key)
        field = self.field

        header_str = f"Specify {self.humankey}{self.appendstr}"
        if unit is not None and self.key != "slice_timing":
            header_str += f" in {unit}"

        self._append_view.append(header_str)

        self.aliases = {}
        self.possible_options = None

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
                    "Import from file",
                ]

            if choices is None:
                choices = [*field.validate.choices]

            if set(space_codes).issubset(choices):
                choices = [*space_codes]
                if self.key == "slice_encoding_direction":
                    choices = list(reversed(choices))[:2]  # hide uncommon options
                display_choices = [display_str(direction_code_str(choice, None)) for choice in choices]

            if display_choices is None:
                display_choices = [display_str(choice) for choice in choices]

            self.aliases = dict(zip(display_choices, choices, strict=False))
            self.possible_options = dict(zip(choices, display_choices, strict=False))

            print("aaaaaaaaaaa self.aliases", self.aliases)
            #    self.input_view: CallableView = SingleChoiceInputView(display_choices, is_vertical=True)
            self.input_view += display_choices
            # mount selection choice,             display_choices

            self.app.push_screen(
                SelectionModal(
                    title="Select value",
                    instructions=header_str,
                    options=self.possible_options,
                    id="set_value_modal",
                ),
                self.next,
            )

            print("display_choicesdisplay_choices00aaaaaaaaaaaaaaaaaaaaaaaa", display_choices)
            print("possible_optionspossible_optionspossible_optionspossible_options", self.possible_options)

        elif isinstance(field, fields.Float):
            self.input_view.append("this requires a number input from the user")
            # mount input modal
            self.app.push_screen(
                SetValueModal(
                    title="Set value",
                    instructions=header_str,
                    id="select_value_modal",
                ),
                self.next,
            )
        else:
            raise ValueError(f'Unsupported metadata field "{field}"')

        self._append_view = self._append_view + self.input_view
        # self._append_view(SpacerView(1))
        print("00aaaaaaaaaaaaaaaaaaaaaaaa", self._append_view)
        print("01aaaaaaaaaaaaaaaaaaaaaaaa", self.input_view)
        return "finished"

    # def run(self, _):
    # self.result = self.input_view
    # if self.result is None:
    # return False
    # return True

    def next(self, result):
        print("ccccccccccccccccccccccccccc222", result)
        if self.possible_options is not None:
            self.callback_message[self.humankey] = [str(self.possible_options[result]) + "\n"]
        else:
            self.callback_message[self.humankey] = [str(result) + "\n"]

        if result is not None:
            key = self.key
            value = result

            if value in self.aliases:
                value = self.aliases[value]

            if key == "slice_timing":
                if value == "import from file":
                    return SliceTimingFileStep(
                        self.app,
                        self.filters,
                        self.schema,
                        self.suggestion,
                        #                 self.next_step_type,
                        appendstr=self.appendstr,
                    )
                else:  # a code was specified
                    key = "slice_timing_code"
                    self.field = _get_field(self.schema, key)

            value = self.field.deserialize(value)

            if self.filters is None:
                specfileobjs: Iterable[File] = [ctx.spec.files[-1]]
            else:
                filepaths = ctx.database.get(**self.filters)
                specfileobjs = set(ctx.database.specfileobj(filepath) for filepath in filepaths)

            for specfileobj in specfileobjs:
                if not hasattr(specfileobj, "metadata"):
                    specfileobj.metadata = dict()
                #  if "metadata" not in ctx.cache[self.id_key]["files"][self.sub_id_key]:
                #      ctx.cache[self.id_key]["files"][self.sub_id_key]["metadata"] = dict()
                specfileobj.metadata[key] = value
                #  ctx.cache[self.id_key]["files"][self.sub_id_key]["metadata"][key] = value

                ctx.cache[self.id_key]["files"] = specfileobj  # type: ignore[assignment]
                print("sssssssssssssssspecfileobjspecfileobjspecfileobj", specfileobj)

                print("vvvvvvvvvvvvvvvvvvvvvvvvvalue", value)
        print("2aaaaaaaaaaaaaaaaaaaaaaaa", self._append_view)
        print("3aaaaaaaaaaaaaaaaaaaaaaaa", self.input_view)
        #     self.callback_message += self._append_view

        if self.next_step_type is not None:
            self.next_step_instance = self.next_step_type(
                app=self.app,
                callback=self.callback,
                callback_message=self.callback_message,
                id_key=self.id_key,
                sub_id_key=self.sub_id_key,
            )
            self.next_step_instance.run()
            # self.next_step_type(app=self.app)
        else:
            if self.callback is not None:
                self.callback(self.callback_message)


class SimpleTestClass:
    test = "bla"

    def __init__(self):
        print("wwwwwwwwwwwwwwwwwwwwwwwwwwwas initiated", self.test)


class SubSimpleTestClass2(SimpleTestClass):
    test = "alb"
    # def __init__(self):
    #   print('wwwwwwwwwwwwwwwwwwwwwwwwwwwas initiated', self.test)


class CheckMetadataStep:
    test = "bla"

    schema: ClassVar[Type[Schema]]

    key: ClassVar[str]
    appendstr: ClassVar[str] = ""

    filters: ClassVar[Optional[Dict[str, str]]] = None

    next_step_type: Type[CheckMetadataStep] | None = None

    show_summary: ClassVar[bool] = True

    def _should_skip(self, _):
        return False

    def __init__(self, app=None, callback=None, callback_message=None, id_key="", sub_id_key=None):
        # def setup(self, ctx):

        self.app = app
        self.callback = callback
        self.humankey = display_str(self.key)
        self.callback_message = callback_message if callback_message is not None else {self.humankey: []}
        if callback_message is not None:
            self.callback_message.update({self.humankey: []})
        print(
            "wwwwwwwwwwwwwwwwwwwwwwwwwwwas initiated callback_message",
            callback_message,
            self.callback_message,
        )
        self.id_key = id_key
        self.sub_id_key = sub_id_key

        self.is_first_run = True
        self.should_skip = self._should_skip(ctx)
        self.choice = None
        self._append_view = []
        self.input_view = []
        if self.should_skip:
            self.is_missing = True
            return

    #   self.next_step_type = next_step_type

    def evaluate(self):
        print("ssssssssssssssssssssselft", self)
        #   print('ssssssssssssssssssssssssssssssss', self.next_step_type)

        if self.filters is None:
            filepaths = [fileobj.path for fileobj in ctx.database.fromspecfileobj(ctx.spec.files[-1])]
        else:
            filepaths = [*ctx.database.get(**self.filters)]

        ctx.database.fillmetadata(self.key, filepaths)

        vals = [ctx.database.metadata(filepath, self.key) for filepath in filepaths]
        self.suggestion = None

        if self.key in ["phase_encoding_direction", "slice_encoding_direction"]:
            for i, val in enumerate(vals):
                if val is not None:
                    vals[i] = direction_code_str(val, filepaths[i])

        elif self.key == "slice_timing":
            for i, val in enumerate(vals):
                if val is not None:
                    sts = slice_timing_str(val)
                    if "unknown" in sts:
                        val = np.array(val)
                        sts = np.array2string(val, max_line_width=256)
                        if len(sts) > 128:
                            sts = f"{sts[:128]}..."
                    else:
                        sts = humanize(sts)
                    vals[i] = sts

        if any(val is None for val in vals):
            self.is_missing = True

            if self.show_summary is True:
                self._append_view.append(f"Missing {self.humankey} values\n")

            vals = [val if val is not None else "missing" for val in vals]
        else:
            self.is_missing = False
            self._append_view.append(f"Check {self.humankey} values{self.appendstr}\n")
        #  self.evaluated_object = f"{self.humankey} values{self.appendstr}"

        assert isinstance(vals, list)

        print("vvvvvvvvvvvvvals", vals)
        uniquevals, counts = np.unique(vals, return_counts=True)
        order = np.argsort(counts)

        column1 = []
        for i in range(min(10, len(order))):
            column1.append(f"{counts[i]} images")
        column1width = max(len(s) for s in column1)
        print("ccccccccccccccccc", column1width)
        unit = _get_unit(self.schema, self.key)
        if unit is None:
            unit = ""

        if self.key == "slice_timing":
            unit = ""

        if self.show_summary is True:
            for i in range(min(10, len(order))):
                display = display_str(f"{uniquevals[i]}")
                if self.suggestion is None:
                    self.suggestion = display
                tablerow = f" {column1[i]:>{column1width}} - {display}"
                if uniquevals[i] != "missing":
                    tablerow = f"{tablerow} {unit}"
                self._append_view.append(tablerow + "\n")
                self.callback_message[self.humankey].append(tablerow + "\n")
            #           self._append_view(TextView(tablerow))

            if len(order) > 10:
                self._append_view.append("...")

        #   print("0000aaaaaaaaaaaa", self._append_view)

        if self.is_missing is False:
            self._append_view.append("Proceed with these values?")
            self.input_view.append("users yes/no choice")
            # here i need to rise modal with yes/no
            # self._append_view(self.input_view)

        if self.show_summary is True or self.is_missing is False:
            pass
            # self._append_view(SpacerView(1))

    def run(self):
        self.evaluate()

        # def run(self, _):
        if self.is_missing:
            # print('hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhere')
            self.app.push_screen(
                Confirm(
                    " ".join(self._append_view),
                    left_button_text=False,
                    right_button_text="OK",
                    #  left_button_variant=None,
                    right_button_variant="default",
                    title="Missing images",
                    id="missing_images_modal",
                    classes="confirm_warning",
                ),
                self.next,
            )
        # if self.callback is not None:
        #    self.callback()
        # return self.is_first_run
        # else:
        # self.choice = self.input_view()
        # if self.choice is None:
        # return False
        # return True
        else:
            print("aaaaaaaaaaaa", self._append_view)
            print("aaaaaaaaaaaa", self.input_view)

            # rise modal here
            self.app.push_screen(
                Confirm(
                    " ".join(self._append_view),
                    left_button_text="YES",
                    right_button_text="NO",
                    left_button_variant="error",
                    right_button_variant="success",
                    title="Check meta data",
                    id="check_meta_data_modal",
                    classes="confirm_warning",
                ),
                self.next,
            )
        # self.app.message = self._append_view

    # return 'finished'

    def next(self, choice):
        # if self.is_first_run or not self.is_missing:
        # self.is_first_run = False
        # choice = 'No'
        print("self.callback_messageself.callback_messageself.callback_message", self.callback_message)

        self.test_text = "wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwas at next"
        print("cccccccccccccccccchoice", choice)
        #     self.callback_message += self._append_view[1:-1]
        if choice is True and self.next_step_type is not None:
            print(" choice is True *********************************************************************")
            next_step_instance = self.next_step_type(
                app=self.app,
                callback=self.callback,
                callback_message=self.callback_message,
                id_key=self.id_key,
                sub_id_key=self.sub_id_key,
            )
            next_step_instance.run()
        # pass
        # this is not correct, should try to trigger next step maybe...........................................
        #  if self.next_step_type is not None:
        #  self.next_step_type(app=self.app)
        # assert self.next_step_type is not None
        # return self.next_step_type(self.app)(ctx)
        elif choice is True and self.next_step_type is None:
            self.callback(self.callback_message)
        elif choice is False:
            print(" choice is False xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx SetMetadataStepSetMetadataStepSetMetadataStep")
            set_instance_step = SetMetadataStep(
                self.filters,
                self.schema,
                self.key,
                self.suggestion,
                appendstr=self.appendstr,
                app=self.app,
                next_step_type=self.next_step_type,
                callback=self.callback,
                callback_message=self.callback_message,
                id_key=self.id_key,
                sub_id_key=self.sub_id_key,
            )
            set_instance_step.run()

    # # def test(self):
    # # print( 'ggggggggggggggggggggggg')

    # return self._append_view


class SubSimpleTestClass(CheckMetadataStep):
    test = "alb"
    # def __init__(self):
    #   print('wwwwwwwwwwwwwwwwwwwwwwwwwwwas initiated', self.test)

    # # def setup(self):
    # self.test_text = '00000000000000000000000000000000000000'
    # print('cccccccccccccccccccccccccccreating class')
    # print(self.next_step_type)
    #    self.run()


class CheckPhaseDiffEchoTimeDiffStep(CheckMetadataStep):
    schema = PhaseDiffFmapFileSchema
    key = "echo_time_difference"
    # next_step_type = HasMoreFmapStep


class CheckPhase1EchoTimeStep(CheckMetadataStep):
    schema = PhaseFmapFileSchema
    key = "echo_time"


# next_step_type = Phase2Step


class CheckPhase2EchoTimeStep(CheckMetadataStep):
    schema = PhaseFmapFileSchema
    key = "echo_time"
    # next_step_type = HasMoreFmapStep


class CheckBoldPhaseEncodingDirectionStep(CheckMetadataStep):
    schema = BoldFileSchema

    key = "phase_encoding_direction"
    appendstr = " for the functional data"
    bold_filedict = {"datatype": "func", "suffix": "bold"}
    filters = bold_filedict

    # next_step_type = fmap_next_step_type


class CheckBoldEffectiveEchoSpacingStep(CheckMetadataStep):
    schema = BoldFileSchema

    key = "effective_echo_spacing"
    appendstr = " for the functional data"
    bold_filedict = {"datatype": "func", "suffix": "bold"}
    filters = bold_filedict
    next_step_type = CheckBoldPhaseEncodingDirectionStep
    filedict = {"datatype": "fmap"}

    def _should_skip(self, ctx):
        filedict = {"datatype": "fmap"}
        filepaths = [*ctx.database.get(**filedict)]
        suffixvalset = ctx.database.tagvalset("suffix", filepaths=filepaths)
        return suffixvalset.isdisjoint(["phase1", "phase2", "phasediff"])


class CheckRepetitionTimeStep(CheckMetadataStep):
    key = "repetition_time"

    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}
    schema = BoldFileSchema


# TODO ASAP
class AcqToTaskMappingStep:
    filedict = {"datatype": "fmap"}
    bold_filedict = {"datatype": "func", "suffix": "bold"}

    def __init__(self, app=None, callback=None, callback_message=None, id_key="", sub_id_key=None):
        # def setup(self, ctx):
        self.is_first_run = True

        self.result = None
        self.app = app
        self.callback = callback

        self.callback = callback
        self.callback_message = callback_message if callback_message is not None else {"AcqToTaskMapping": []}
        if callback_message is not None:
            self.callback_message.update({"AcqToTaskMapping": []})

    def evaluate(self):
        fmapfilepaths = ctx.database.get(**self.filedict)
        fmaptags = sorted(
            set(
                frozenset(
                    (k, v)
                    for k, v in ctx.database.tags(f).items()
                    if k not in ["sub", "dir"] and k in entities and v is not None
                )
                for f in fmapfilepaths
            )
        )
        fmaptags = [f for f in fmaptags if f != frozenset()]  # do not include empty set!
        self.fmaptags = fmaptags

        boldfilepaths = ctx.database.get(**self.bold_filedict)
        boldtags = sorted(
            set(
                frozenset(
                    (k, v) for k, v in ctx.database.tags(f).items() if k not in ["sub"] and k in entities and v is not None
                )
                for f in boldfilepaths
            )
        )
        self.boldtags = boldtags
        print("fffffffffffffffffffffffff self.fmaptags", self.fmaptags)
        print("fffffffffffffffffffffffff self.boldtags", self.boldtags)

        print("eeeeeeeeeeeeeeeeeeeeeeeee", entities)

        print("fffffffffffffffffffffffff fmapfilepaths", fmapfilepaths)

        for f in fmapfilepaths:
            for k, v in ctx.database.tags(f).items():
                #     if k not in ["sub"] and k in entities and v is not None:
                print("kkkkkkkkkkkvvvvvvvvvvvvvvvffffffffffff", k, v, f)

        if len(fmaptags) > 0:

            def _format_tags(tagset, break_lines=False):
                tagdict = dict(tagset)
                if break_lines is True:
                    break_char = "\n"
                else:
                    break_char = ""
                return ", ".join(
                    (
                        f'{break_char}{e}:"{tagdict[e]}"'
                        if e not in entity_longnames
                        else f'{entity_longnames[e]} "{tagdict[e]}"'
                    )
                    for e in entities
                    if e in tagdict and tagdict[e] is not None
                )

            self.is_predefined = False

            self._append_view = []
            self.input_view = []
            self._append_view.append("Assign field maps to functional images")

            self.options = [_format_tags(t).capitalize() for t in boldtags]
            self.values = [f"Field map {_format_tags(t, break_lines=True)}".strip() for t in fmaptags]
            selected_indices = [self.fmaptags.index(o) if o in fmaptags else 0 for o in boldtags]

            self.input_view.append(([*self.options], [*self.values], selected_indices))
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXx self._append_view, self.input_view", self._append_view, self.input_view)
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXx111 fmaptags", fmaptags)
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXx222 values", self.values)

            print("XXXXXXXXXXXXXXXXXXXXXXXXXXx333 self.options", self.options)

            print("XXXXXXXXXXXXXXXXXXXXXXXXXXx444 boldtags", boldtags)
            #            self._append_view(self.input_view)
            #       self._append_view(SpacerView(1))

            for option, boldtagset in zip(self.options, self.boldtags, strict=False):
                print("option:::", option, "       boldtagset:::", boldtagset)

        else:
            self.is_predefined = True

    def run(self):
        self.evaluate()

        if self.is_predefined:
            self.next(None)
        #    return self.is_first_run
        else:
            # rise modal here
            self.app.push_screen(
                MultipleRadioSetModal(horizontal_label_set=self.values, vertical_label_set=self.options), self.next
            )

    #            self.result = self.input_view
    #  if self.result is None:
    #      return False
    #    return True

    def next(self, results):
        if results is not None:
            # fmaptags = [frozenset({('task', 'test1')}), frozenset({('task', 'rest_bold')}), frozenset({('task', 'test2')}),
            #   frozenset({('task', 'test3-1')}), frozenset({('task', 'test3-2')})]
            # values= ['Field map task "test1"', 'Field map task "rest_bold"', 'Field map task "test2"',
            #   'Field map task "test3-1"', 'Field map task "test3-2"']
            # options = ['Task "rest_bold"', 'Task "blabla_bold"']
            # {boldtags[1]: fmaptags[values.index('Field map task "test2"')]}
            # {frozenset({('task', 'blabla_bold')}): frozenset({('task', 'test2')})}
            # For the option from the options list the result will output some of the value from the values list which will
            # then give the index in the values list which is then used to select the right object from the fmaptags
            # self.result[option] is some value from the value list

            # bold_fmap_tag_dict = {
            # boldtagset: self.fmaptags[self.values.index(result[option])]
            # for option, boldtagset in zip(self.options, self.boldtags, strict=False)
            # }
            #   self.callback_message["AcqToTaskMapping"] = {option: results[option] for i, option in enumerate(self.options)}
            self.callback_message["AcqToTaskMapping"] = [
                f"{key} >===< {self.values[results[key]]}".replace("\n", "") + "\n" for key in results
            ]

            bold_fmap_tag_dict = {
                boldtagset: self.fmaptags[results[option]]
                for option, boldtagset in zip(self.options, self.boldtags, strict=False)
            }

            #  for option, boldtagset in zip(self.options, self.boldtags, strict=False):
            #      print(option, boldtagset)

            fmap_bold_tag_dict = dict()
            for boldtagset, fmaptagset in bold_fmap_tag_dict.items():
                if fmaptagset not in fmap_bold_tag_dict:
                    fmap_bold_tag_dict[fmaptagset] = boldtagset
                else:
                    fmap_bold_tag_dict[fmaptagset] = fmap_bold_tag_dict[fmaptagset] | boldtagset

            #                 ctx.cache[self.id_key]["files"] = specfileobj

            for specfileobj in ctx.spec.files:
                if specfileobj.datatype != "fmap":
                    continue

                print("pppppppppppppppppppppppppppppppppp specfileobj.path", specfileobj.path)

                fmaplist = ctx.database.fromspecfileobj(specfileobj)

                fmaptags = set(
                    frozenset(
                        (k, v) for k, v in ctx.database.tags(f).items() if k not in ["sub"] and k in entities and v is not None
                    )
                    for f in map(attrgetter("path"), fmaplist)
                )

                def _expand_fmaptags(tagset):
                    if any(a == "acq" for a, _ in tagset):
                        return tagset
                    else:
                        return tagset | frozenset([("acq", "null")])

                mappings = set(
                    (a, b)
                    for fmap in fmaptags
                    for a, b in product(
                        fmap_bold_tag_dict.get(fmap, list()),
                        _expand_fmaptags(fmap),
                    )
                    if a[0] != b[0] and "sub" not in (a[0], b[0])
                )

                intended_for: dict[str, list[str]] = dict()
                for functag, fmaptag in mappings:
                    entity, val = functag
                    funcstr = f"{entity}.{val}"
                    entity, val = fmaptag
                    fmapstr = f"{entity}.{val}"
                    if fmapstr not in intended_for:
                        intended_for[fmapstr] = list()
                    intended_for[fmapstr].append(funcstr)

                specfileobj.intended_for = intended_for

                for name in ctx.cache:
                    if ctx.cache[name]["files"] != {}:
                        if ctx.cache[name]["files"].path == specfileobj.path:  # type: ignore[attr-defined]
                            ctx.cache[name]["files"].intended_for = intended_for  # type: ignore[attr-defined]

        # if self.is_first_run or not self.is_predefined:
        #    self.is_first_run = False
        # return CheckBoldEffectiveEchoSpacingStep(self.app)
        next_step_instance = CheckBoldEffectiveEchoSpacingStep(
            app=self.app,
            callback=self.callback,
            callback_message=self.callback_message,
            # id_key=self.id_key,
            #  sub_id_key=self.sub_id_key,
        )
        next_step_instance.run()


class CheckBoldSliceTimingStep(CheckMetadataStep):
    schema = BoldFileSchema
    filetype_str = "BOLD image"
    key = "slice_timing"
    filters = {"datatype": "func", "suffix": "bold"}

    def _should_skip(self, ctx):
        if self.key in ctx.already_checked:
            return True
        ctx.already_checked.add(self.key)
        return False


class CheckBoldSliceEncodingDirectionStep(CheckMetadataStep):
    schema = BoldFileSchema
    filetype_str = "BOLD image"
    key = "slice_encoding_direction"
    filters = {"datatype": "func", "suffix": "bold"}

    next_step_type = CheckBoldSliceTimingStep

    def _should_skip(self, ctx):
        if self.key in ctx.already_checked:
            return True
        ctx.already_checked.add(self.key)
        return False
