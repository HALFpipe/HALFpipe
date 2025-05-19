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
from ...model.file.ref import RefFileSchema
from ...model.metadata import slice_order_strs, space_codes
from ...model.tags import entities, entity_longnames
from ..data_analyzers.context import ctx
from ..general_widgets.multichoice_radioset import MultipleRadioSetModal
from ..general_widgets.selection_modal import SelectionModal
from ..general_widgets.set_value_modal import SetValueModal

# from ..logging import logger
from ..specialized_widgets.confirm_screen import Confirm
from ..standards import display_str


def _get_field(schema, key):
    """
    Retrieves a field from a schema by key.

    Parameters
    ----------
    schema : Schema or type
        The schema or schema type to search within.
    key : str
        The key of the field to retrieve.

    Returns
    -------
    Field or None
        The field object if found, otherwise None.
    """
    if isinstance(schema, type):
        instance = schema()
    else:
        instance = schema
    if "metadata" in instance.fields:
        return _get_field(instance.fields["metadata"].nested, key)
    return instance.fields.get(key)


def _get_unit(schema, key):
    """
    Retrieves the unit of a field from a schema.

    Parameters
    ----------
    schema : Schema or type
        The schema or schema type to search within.
    key : str
        The key of the field to retrieve the unit for.

    Returns
    -------
    str or None
        The unit of the field if found, otherwise None.
    """
    field = _get_field(schema, key)
    if field is not None:
        return field.metadata.get("unit")


class SliceTimingFileStep:
    """
    Handles the step of importing slice timing values from a file.

    Attributes
    ----------
    key : str
        The key for slice timing.
    """

    key = "slice_timing"

    def _messagefun(self):
        return self.message

    def __init__(self, app, filters, schema, suggestion, appendstr=""):
        """
        Initializes the SliceTimingFileStep.

        Parameters
        ----------
        app : Any
            The application object.
        filters : dict
            Filters for selecting files.
        schema : Schema or type
            The schema or schema type.
        suggestion : Any
            A suggestion for the user.
        appendstr : str, optional
            A string to append to the header, by default "".
        """
        self.app = app
        self.schema = schema
        self.field = _get_field(self.schema, self.key)
        self.appendstr = appendstr

        self.suggestion = suggestion
        self.message = None

        self.filters = filters

        self._append_view = []
        self.input_view: list = []

        # SETUP
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

        # RUN
        while True:
            self.result = self.input_view[0]

            if self.result is None:
                return False

            # validate

            filepath = self.result
            try:
                spreadsheet = read_spreadsheet(filepath)
                # valuearray = np.ravel(spreadsheet.values).astype(np.float64)
                valuearray = np.ravel(np.array(spreadsheet.values, dtype=np.float64))
                valuelist = valuearray.tolist()
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
                                f"Slice timing from file has {len(value):d} values, but scans have {n_slices:d} slices"
                            )

                    for i, time in enumerate(value):
                        if time > repetition_time:
                            raise ValueError(
                                f"Invalid time for slice {i + 1:d}: "
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


class SetMetadataStep:
    """
    Handles the step of setting metadata values. Offers either a selection list (slice
    timing order, encoding direction) or a input prompt for a custom user's value.

    Attributes
    ----------
    schema : Schema or type
        The schema or schema type.
    key : str
        The key for the metadata.
    field : Field
        The field object.
    appendstr : str
        A string to append to the header.
    suggestion : Any
        A suggestion for the user.
    filters : dict
        Filters for selecting files.
    _append_view : list[str]
        List of strings to append to the view.
    input_view : list[str]
        List of strings for user input.
    app : Any
        The application object.
    next_step_type : Type[CheckMetadataStep] or None
        The type of the next step.
    callback : Callable or None
        A callback function.
    humankey : str
        The human-readable key.
    id_key : str
        The ID key.
    sub_id_key : str or None
        The sub-ID key.
    callback_message : dict
        A dictionary for callback messages.
    aliases : dict
        A dictionary of aliases.
    possible_options : dict or None
        A dictionary of possible options.
    """

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
        """
        Initializes the SetMetadataStep.

        Parameters
        ----------
        filters : dict
            Filters for selecting files.
        schema : Schema or type
            The schema or schema type.
        key : str
            The key for the metadata.
        suggestion : Any
            A suggestion for the user.
        appendstr : str, optional
            A string to append to the header, by default "".
        app : Any, optional
            The application object, by default None.
        next_step_type : Type[CheckMetadataStep] or None, optional
            The type of the next step, by default None.
        callback : Callable or None, optional
            A callback function, by default None.
        callback_message : dict or None, optional
            A dictionary for callback messages, by default None.
        id_key : str, optional
            The ID key, by default "".
        sub_id_key : str or None, optional
            The sub-ID key, by default None.
        """
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

    async def run(self):
        """
        Runs the metadata setting process.
        """
        # SETUP
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

            self.input_view += display_choices

            choice = await self.app.push_screen_wait(
                SelectionModal(
                    title="Select value",
                    instructions=header_str,
                    options=self.possible_options,
                    only_ok_button=True,
                    id="set_value_modal",
                )
            )
            await self.next(choice)

        elif isinstance(field, fields.Float):
            self.input_view.append("this requires a number input from the user")
            # mount input modal
            choice = await self.app.push_screen_wait(
                SetValueModal(
                    title="Set value",
                    instructions=header_str,
                    left_button_text="OK",
                    right_button_text=False,
                    left_button_variant="default",
                    id="select_value_modal",
                )
            )
            await self.next(choice)

        else:
            raise ValueError(f'Unsupported metadata field "{field}"')

    async def next(self, result):
        """
        Handles the next step after setting metadata.

        Parameters
        ----------
        result : Any
            The result of the metadata setting process.
        """
        if result is not False:
            if self.possible_options is not None:
                self.callback_message[self.humankey] = [str(self.possible_options[result]) + "\n"]
            else:
                self.callback_message[self.humankey] = [str(result) + "\n"]
        else:
            self.callback_message[self.humankey] = ["default value" + "\n"]

        if result is not False:
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
                specfileobj.metadata[key] = value

            # update all fileobjs in the ctx.cache, we use the filters to filter only those to which this applies
            for widget_id, the_dict in ctx.cache.items():
                # should always be there
                if "files" in the_dict:
                    if isinstance(the_dict["files"], File):
                        is_ok = True
                        if self.filters is not None:
                            if the_dict["files"].datatype != self.filters.get("datatype"):
                                is_ok = False
                            if the_dict["files"].suffix != self.filters.get("suffix"):
                                is_ok = False
                        if is_ok:
                            # add dict if it does not exist
                            if not hasattr(ctx.cache[widget_id]["files"], "metadata"):
                                ctx.cache[widget_id]["files"].metadata = dict()
                            ctx.cache[widget_id]["files"].metadata[key] = value

        if self.next_step_type is not None:
            self.next_step_instance = self.next_step_type(
                app=self.app,
                callback=self.callback,
                callback_message=self.callback_message,
                id_key=self.id_key,
                sub_id_key=self.sub_id_key,
            )
            await self.next_step_instance.run()
        else:
            if self.callback is not None:
                return self.callback(self.callback_message)
            else:
                return None


class CheckMetadataStep:
    """
    Base class for checking metadata values.

    This class provides a framework for checking metadata values associated
    with files in the database. It evaluates whether metadata is missing,
    displays a summary of the metadata values, and prompts the user to
    confirm or modify the values.

    Attributes
    ----------
    schema : ClassVar[Type[Schema]]
        The schema used to validate the metadata.
    key : ClassVar[str]
        The key for the metadata to check.
    appendstr : ClassVar[str], optional
        A string to append to the header, by default "".
    filters : ClassVar[Optional[Dict[str, str]]], optional
        Filters for selecting files, by default None.
    next_step_type : Type[CheckMetadataStep] | None, optional
        The type of the next step, by default None.
    show_summary : ClassVar[bool], optional
        Whether to show a summary of the metadata values, by default True.
    app : Any, optional
        The application object, by default None.
    callback : Callable, optional
        A callback function, by default None.
    callback_message : dict, optional
        A dictionary for callback messages, by default None.
    id_key : str, optional
        The ID key, by default "".
    sub_id_key : str, optional
        The sub-ID key, by default None.
    humankey : str
        The human-readable key.
    is_first_run : bool
        Flag indicating if it's the first run.
    should_skip : bool
        Flag indicating if the step should be skipped.
    choice : Any
        The user's choice.
    _append_view : list[str]
        List of strings to append to the view.
    input_view : list[str]
        List of strings for user input.
    is_missing : bool
        Flag indicating if metadata is missing.
    suggestion : Any
        A suggestion for the user.
    """

    schema: ClassVar[Type[Schema]]

    key: ClassVar[str]
    appendstr: ClassVar[str] = ""

    filters: ClassVar[Optional[Dict[str, str]]] = None

    next_step_type: Type[CheckMetadataStep] | None = None

    show_summary: ClassVar[bool] = True

    def _should_skip(self, _):
        return False

    def __init__(self, app=None, callback=None, callback_message=None, id_key="", sub_id_key=None):
        """
        Initializes the CheckMetadataStep.

        Parameters
        ----------
        app : Any, optional
            The application object, by default None.
        callback : Callable, optional
            A callback function, by default None.
        callback_message : dict, optional
            A dictionary for callback messages, by default None.
        id_key : str, optional
            The ID key, by default "".
        sub_id_key : str, optional
            The sub-ID key, by default None.
        """
        # SETUP
        self.app = app
        self.callback = callback
        self.humankey = display_str(self.key)
        self.callback_message = callback_message if callback_message is not None else {self.humankey: []}
        if callback_message is not None:
            self.callback_message.update({self.humankey: []})

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

    def evaluate(self):
        """
        Evaluates the metadata values.

        This method retrieves metadata values from the database, checks if
        any values are missing, and prepares a summary of the values.
        """
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

        assert isinstance(vals, list)

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

            if len(order) > 10:
                self._append_view.append("...")

        if self.is_missing is False:
            self._append_view.append("Proceed with these values?")
            self.input_view.append("users yes/no choice")
            # here i need to rise modal with yes/no
            # self._append_view(self.input_view)

        if self.show_summary is True or self.is_missing is False:
            pass

    async def run(self):
        """
        Runs the metadata checking process.

        This method evaluates the metadata, displays a summary or a warning
        if metadata is missing, and prompts the user to proceed or modify
        the values.
        """
        self.evaluate()

        # def run(self, _):
        if self.is_missing:
            choice = await self.app.push_screen_wait(
                Confirm(
                    " ".join(self._append_view),
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Missing images",
                    id="missing_images_modal",
                    classes="confirm_warning",
                )
            )
            await self.next(choice)
        else:
            # rise modal here
            choice = await self.app.push_screen_wait(
                Confirm(
                    " ".join(self._append_view),
                    left_button_text="YES",
                    right_button_text="NO",
                    left_button_variant="error",
                    right_button_variant="success",
                    title="Check meta data",
                    id="check_meta_data_modal",
                    classes="confirm_warning",
                )
            )
            await self.next(choice)

    async def next(self, choice):
        """
        Handles the next step after checking metadata.

        Parameters
        ----------
        choice : bool
            The user's choice (True for proceed, False for modify).
        """
        if choice is True and self.next_step_type is not None:
            next_step_instance = self.next_step_type(
                app=self.app,
                callback=self.callback,
                callback_message=self.callback_message,
                id_key=self.id_key,
                sub_id_key=self.sub_id_key,
            )
            await next_step_instance.run()

        elif choice is True and self.next_step_type is None:
            return self.callback(self.callback_message)
        elif choice is False:
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
            await set_instance_step.run()
        else:
            pass


class CheckPhaseDiffEchoTime2Step(CheckMetadataStep):
    schema = PhaseDiffFmapFileSchema
    key = "echo_time2"
    # next_step_type = HasMoreFmapStep


class CheckPhaseDiffEchoTime1Step(CheckMetadataStep):
    schema = PhaseDiffFmapFileSchema
    key = "echo_time1"
    next_step_type = CheckPhaseDiffEchoTime2Step


class CheckPhase1EchoTimeStep(CheckMetadataStep):
    """
    Checks the echo time for the first set of phase images.

    This class extends CheckMetadataStep to specifically handle the echo
    time metadata for the first set of phase images.

    Attributes
    ----------
    schema : ClassVar[Type[PhaseFmapFileSchema]]
        The schema for phase field map files.
    key : ClassVar[str]
        The metadata key for echo time.
    """

    schema = PhaseFmapFileSchema
    key = "echo_time"
    # next_step_type = Phase2Step


class CheckPhase2EchoTimeStep(CheckMetadataStep):
    """
    Checks the echo time for the second set of phase images.

    This class extends CheckMetadataStep to specifically handle the echo
    time metadata for the second set of phase images.

    Attributes
    ----------
    schema : ClassVar[Type[PhaseFmapFileSchema]]
        The schema for phase field map files.
    key : ClassVar[str]
        The metadata key for echo time.
    """

    schema = PhaseFmapFileSchema
    key = "echo_time"
    # next_step_type = HasMoreFmapStep


class CheckBoldPhaseEncodingDirectionStep(CheckMetadataStep):
    """
    Checks the phase encoding direction for BOLD files.

    This class extends CheckMetadataStep to specifically handle the phase
    encoding direction metadata for BOLD files.

    Attributes
    ----------
    schema : ClassVar[Type[BoldFileSchema]]
        The schema for BOLD files.
    key : ClassVar[str]
        The metadata key for phase encoding direction.
    appendstr : ClassVar[str]
        A string to append to the header.
    filters : ClassVar[Dict[str, str]]
        Filters for selecting BOLD files.
    """

    schema = BoldFileSchema

    key = "phase_encoding_direction"
    appendstr = " for the functional data"
    bold_filedict = {"datatype": "func", "suffix": "bold"}
    filters = bold_filedict

    # next_step_type = fmap_next_step_type


class CheckBoldEffectiveEchoSpacingStep(CheckMetadataStep):
    """
    Checks the effective echo spacing for BOLD files.

    This class extends CheckMetadataStep to specifically handle the effective
    echo spacing metadata for BOLD files.

    Attributes
    ----------
    schema : ClassVar[Type[BoldFileSchema]]
        The schema for BOLD files.
    key : ClassVar[str]
        The metadata key for effective echo spacing.
    appendstr : ClassVar[str]
        A string to append to the header.
    filters : ClassVar[Dict[str, str]]
        Filters for selecting BOLD files.
    next_step_type : Type[CheckBoldPhaseEncodingDirectionStep]
        The type of the next step.
    filedict : Dict[str, str]
        The file dictionary for field map files.
    """

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
    """
    Checks the repetition time for BOLD files.

    This class extends CheckMetadataStep to specifically handle the
    repetition time metadata for BOLD files.

    Attributes
    ----------
    key : ClassVar[str]
        The metadata key for repetition time.
    filetype_str : str
        The file type string for BOLD images.
    filters : Dict[str, str]
        Filters for selecting BOLD files.
    schema : Type[BoldFileSchema]
        The schema for BOLD files.
    """

    key = "repetition_time"

    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}
    schema = BoldFileSchema


# TODO ASAP
class AcqToTaskMappingStep:
    """
    Maps acquisition entities to task entities for field map files.

    This class handles the mapping of acquisition entities (e.g., 'acq')
    in field map files to task entities in BOLD files. It presents a
    user interface to define these mappings and updates the specification
    accordingly.

    Attributes
    ----------
    filedict : Dict[str, str]
        The file dictionary for field map files.
    bold_filedict : Dict[str, str]
        The file dictionary for BOLD files.
    app : Any, optional
        The application object, by default None.
    callback : Callable, optional
        A callback function, by default None.
    callback_message : dict, optional
        A dictionary for callback messages, by default None.
    id_key : str, optional
        The ID key, by default "".
    sub_id_key : str, optional
        The sub-ID key, by default None.
    is_first_run : bool
        Flag indicating if it's the first run.
    result : Any
        The user's choice.
    fmaptags : list[frozenset]
        List of tag sets for field map files.
    boldtags : list[frozenset]
        List of tag sets for BOLD files.
    is_predefined : bool
        Flag indicating if the mapping is predefined.
    _append_view : list[str]
        List of strings to append to the view.
    input_view : list[str]
        List of strings for user input.
    options : list[str]
        List of options for BOLD files.
    values : list[str]
        List of values for field map files.
    """

    filedict = {"datatype": "fmap"}
    bold_filedict = {"datatype": "func", "suffix": "bold"}

    def __init__(self, app=None, callback=None, callback_message=None, id_key="", sub_id_key=None):
        """
        Initializes the AcqToTaskMappingStep.

        Parameters
        ----------
        app : Any, optional
            The application object, by default None.
        callback : Callable, optional
            A callback function, by default None.
        callback_message : dict, optional
            A dictionary for callback messages, by default None.
        id_key : str, optional
            The ID key, by default "".
        sub_id_key : str, optional
            The sub-ID key, by default None.
        """
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
        """
        Evaluates the mapping between field map and BOLD files.

        This method retrieves the tags for field map and BOLD files,
        formats them for display, and prepares the options and values
        for the user interface.
        """

        def _format_tags(tagset, break_lines=False):
            tagdict = dict(tagset)
            if break_lines is True:
                break_char = "\n"
            else:
                break_char = ""
            return ", ".join(
                (f'{break_char}{e}:"{tagdict[e]}"' if e not in entity_longnames else f'{entity_longnames[e]} "{tagdict[e]}"')
                for e in entities
                if e in tagdict and tagdict[e] is not None
            )

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
        self.options = [_format_tags(t).capitalize() for t in boldtags]

        if len(fmaptags) > 0:
            self.is_predefined = False

            self._append_view = []
            self.input_view = []
            self._append_view.append("Assign field maps to functional images")

            self.values = [f"Field map {_format_tags(t, break_lines=True)}".strip() for t in fmaptags]
            selected_indices = [self.fmaptags.index(o) if o in fmaptags else 0 for o in boldtags]

            self.input_view.append(([*self.options], [*self.values], selected_indices))

        else:
            self.is_predefined = True

    async def run(self):
        """
        Runs the acquisition-to-task mapping process.

        This method evaluates the mapping and, if necessary, presents a
        user interface to define the mappings.
        """
        self.evaluate()

        if self.is_predefined:
            await self.next(None)
        else:
            # rise modal here
            choice = await self.app.push_screen_wait(
                MultipleRadioSetModal(horizontal_label_set=self.values, vertical_label_set=self.options)
            )
            await self.next(choice)

    async def next(self, results):
        """
        Handles the next step after mapping acquisition to tasks.

        This method processes the user's mapping choices, updates the
        specification with the 'intended_for' field, and proceeds to the
        next step in the pipeline.

        Parameters
        ----------
        results : dict or None
            The user's mapping choices, or None if the mapping is predefined.
        """
        if results is not None:
            self.callback_message["AcqToTaskMapping"] = [
                f"{key} >===< {self.values[results[key].index(True)]}".replace("\n", "") + "\n" for key in results
            ]
            bold_fmap_tag_dict = {
                boldtagset: self.fmaptags[results.get(option).index(True)]
                for option, boldtagset in zip(self.options, self.boldtags, strict=False)
                if results.get(option) is not None
            }
        else:
            # When there is nothing to map, e.g., there was not modal to match the fields with tasks,
            # the field in "acq.null" is still filled out. To not rise unnecessary modal, we create here the
            # bold_fmap_tag_dict so that later this field is filled.
            self.callback_message["AcqToTaskMapping"] = ["No acquisition to task mapping was needed.\n"]
            bold_fmap_tag_dict = {
                boldtagset: frozenset() for option, boldtagset in zip(self.options, self.boldtags, strict=False)
            }
            self.fmaptags = [frozenset()]

        fmap_bold_tag_dict = dict()
        for boldtagset, fmaptagset in bold_fmap_tag_dict.items():
            if fmaptagset not in fmap_bold_tag_dict:
                fmap_bold_tag_dict[fmaptagset] = boldtagset
            else:
                fmap_bold_tag_dict[fmaptagset] = fmap_bold_tag_dict[fmaptagset] | boldtagset

        for specfileobj in ctx.spec.files:
            if specfileobj.datatype != "fmap":
                continue

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
        next_step_instance = CheckBoldEffectiveEchoSpacingStep(
            app=self.app,
            callback=self.callback,
            callback_message=self.callback_message,
        )
        await next_step_instance.run()


class CheckBoldSliceTimingStep(CheckMetadataStep):
    """
    Checks the slice timing for BOLD files.

    This class extends CheckMetadataStep to specifically handle the slice
    timing metadata for BOLD files.

    Attributes
    ----------
    schema : Type[BoldFileSchema]
        The schema for BOLD files.
    filetype_str : str
        The file type string for BOLD images.
    key : str
        The metadata key for slice timing.
    filters : Dict[str, str]
        Filters for selecting BOLD files.
    """

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
    """
    Checks the slice encoding direction for BOLD files.

    This class extends CheckMetadataStep to specifically handle the slice
    encoding direction metadata for BOLD files.

    Attributes
    ----------
    schema : Type[BoldFileSchema]
        The schema for BOLD files.
    filetype_str : str
        The file type string for BOLD images.
    key : str
        The metadata key for slice encoding direction.
    filters : Dict[str, str]
        Filters for selecting BOLD files.
    next_step_type : Type[CheckBoldSliceTimingStep]
        The type of the next step.
    """

    schema = BoldFileSchema
    filetype_str = "BOLD image"
    key = "slice_encoding_direction"
    filters = {"datatype": "func", "suffix": "bold"}

    next_step_type = CheckBoldSliceTimingStep


class CheckSpaceStep(CheckMetadataStep):
    """
    Checks the space for reference files.

    This class extends CheckMetadataStep to specifically handle the space
    metadata for reference files (e.g., atlases, spatial maps, seed maps).

    Attributes
    ----------
    schema : Type[RefFileSchema]
        The schema for reference files.
    key : str
        The metadata key for space.
    """

    schema = RefFileSchema
    key = "space"
