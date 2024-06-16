# -*- coding: utf-8 -*-
from typing import ClassVar, Dict, List, Type, Union

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, RadioButton, RadioSet, Static

from halfpipe.tui.utils.path_pattern_builder import PathPatternBuilder

from ...ingest.glob import get_entities_in_path, tag_parse

# TODO
# For bids, this is automatic message
# Found 0 field map image files
# after putting BOLD images, i need this message
# Check repetition time values
# 18 images - 0.75 seconds
# 36 images - 2.0 seconds
# Proceed with these values?
# [Yes] [No]
# Specify repetition time in seconds
# [0]
# There are 4 SummarySteps: FilePatternSummaryStep, AnatSummaryStep, BoldSummaryStep, FmapSummaryStep
# AnatSummaryStep > BoldSummaryStep > get_post_func_steps > FmapSummaryStep > END
# get_post_func_steps: will now be checked in different tab
# def get_post_func_steps(this_next_step_type: Optional[Type[Step]]) -> Type[Step]:
# class DummyScansStep(Step):
# class CheckBoldSliceTimingStep(CheckMetadataStep):
# class CheckBoldSliceEncodingDirectionStep(CheckMetadataStep):
# class DoSliceTimingStep(YesNoStep):
####################################################################################
from ...model.file.anat import T1wFileSchema
from ...model.file.base import BaseFileSchema, File
from ...model.file.bids import BidsFileSchema
from ...model.file.fmap import (
    BaseFmapFileSchema,
    EPIFmapFileSchema,
    PhaseDiffFmapFileSchema,
    PhaseFmapFileSchema,
)
from ...model.file.func import (
    BoldFileSchema,
    MatEventsFileSchema,
    TsvEventsFileSchema,
    TxtEventsFileSchema,
)
from ...model.file.schema import FileSchema
from ...model.tags import entities
from ...model.tags import entity_longnames as entity_display_aliases
from ...model.utils import get_schema_entities
from ...utils.format import inflect_engine as p
from ...utils.path import split_ext
from ..utils.context import ctx
from ..utils.custom_switch import TextSwitch
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.filebrowser import FileBrowser
from ..utils.list_of_files_modal import ListOfFiles
from ..utils.non_bids_file_itemization import FileItem

entity_colors = {
    "sub": "red",
    "ses": "green",
    "run": "magenta",
    "task": "cyan",
    "dir": "yellow",
    "condition": "orange",
    "desc": "orange",
    "acq": "cyan",
    "echo": "orange",
}


class FilePatternStep:
    entity_display_aliases = entity_display_aliases
    header_str = ""
    ask_if_missing_entities: List[str] = list()
    required_in_path_entities: List[str] = list()

    filetype_str: str = "file"
    filedict: Dict[str, str] = {}
    schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema

    def __init__(
        self,
        path="",
    ):
        self.entities = get_schema_entities(self.schema)  # Assumes a function to extract schema entities
        self.path = path

        # setup
        self.fileobj: File | None = None

        schema_entities = get_schema_entities(self.schema)
        schema_entities = [entity for entity in reversed(entities) if entity in schema_entities]  # keep order
        # convert to display
        self.schema_entities = [
            (self.entity_display_aliases[entity] if entity in self.entity_display_aliases else entity)
            for entity in schema_entities
        ]

        # need original entities for this
        self.entity_colors_list = [entity_colors[entity] for entity in schema_entities]

        self.required_entities = [
            *self.ask_if_missing_entities,
            *self.required_in_path_entities,
        ]

    def _transform_extension(self, ext):
        return ext

    @property
    def get_entities(self):
        return self.schema_entities

    @property
    def get_entity_colors_list(self):
        return self.entity_colors_list

    @property
    def get_required_entities(self):
        return self.required_entities

    def push_path_to_context_obj(self, path):
        # run
        inv = {alias: entity for entity, alias in self.entity_display_aliases.items()}

        i = 0
        _path = ""
        for match in tag_parse.finditer(path):
            groupdict = match.groupdict()
            if groupdict.get("tag_name") in inv:
                _path += path[i : match.start("tag_name")]
                _path += inv[match.group("tag_name")]
                i = match.end("tag_name")

        _path += path[i:]
        path = _path

        # create file obj
        filedict = {**self.filedict, "path": path, "tags": {}}
        _, ext = split_ext(path)
        filedict["extension"] = self._transform_extension(ext)

        loadresult = self.schema().load(filedict)
        assert isinstance(loadresult, File), "Invalid schema load result"
        self.fileobj = loadresult

        # next
        ctx.spec.files.append(self.fileobj)


class AnatStep(FilePatternStep):
    required_in_path_entities = ["subject"]
    header_str = "T1-weighted image file pattern"
    filetype_str = "T1-weighted image"
    filedict = {"datatype": "anat", "suffix": "T1w"}

    schema = T1wFileSchema

    def __init__(self, path=""):
        super().__init__(path=path)


class BoldStep(FilePatternStep):
    ask_if_missing_entities = ["task"]
    required_in_path_entities = ["subject"]
    header_str = "BOLD image file pattern"

    schema = BoldFileSchema
    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}

    def __init__(self, path=""):
        super().__init__(path=path)


def find_bold_file_paths():
    bold_file_paths = ctx.database.get(datatype="func", suffix="bold")

    if bold_file_paths is None:
        raise ValueError("No BOLD files in database")

    #  filters = ctx.spec.settings[-1].get("filters")
    filters = None
    bold_file_paths = set(bold_file_paths)

    if filters is not None:
        bold_file_paths = ctx.database.applyfilters(bold_file_paths, filters)

    return bold_file_paths


class EventsStep(FilePatternStep):
    header_str = "Event file pattern"
    required_in_path_entities: List[str] = list()

    ask_if_missing_entities: List[str] = list()
    filedict = {"datatype": "func", "suffix": "events"}
    filetype_str = "event"

    def __init__(self, path=""):
        super().__init__(path=path)

        # setup
        bold_file_paths = find_bold_file_paths()

        taskset = ctx.database.tagvalset("task", filepaths=bold_file_paths)
        if taskset is None:
            taskset = set()
        self.taskset = taskset

        if len(self.taskset) > 1:
            self.required_in_path_entities = ["task"]
        #        super(EventsStep, self).setup(ctx)

        # next
        if len(self.taskset) == 1:
            assert isinstance(self.fileobj, File)
            if self.fileobj.tags.get("task") is None:
                if "task" not in get_entities_in_path(self.fileobj.path):
                    (self.fileobj.tags["task"],) = self.taskset

    # return super(EventsStep, self).next(ctx)

    #  @abstractmethod
    def _transform_extension(self, ext):
        raise NotImplementedError()


class MatEventsStep(EventsStep):
    schema = MatEventsFileSchema

    def _transform_extension(self, ext):
        assert ext == ".mat"
        return ext


# next_step_type = CheckUnitsStep


class TxtEventsStep(EventsStep):
    schema = TxtEventsFileSchema
    required_in_path_entities = ["condition"]

    def _transform_extension(self, _):
        return ".txt"


class TsvEventsStep(EventsStep):
    schema = TsvEventsFileSchema

    def _transform_extension(self, _):
        return ".tsv"


class FmapFilePatternStep(FilePatternStep):
    bold_filedict = {"datatype": "func", "suffix": "bold"}
    filetype_str = "field map image"
    filetype_str = filetype_str
    filedict = {"datatype": "fmap"}

    def __init__(self, path=""):
        super().__init__(path=path)


class FieldMapStep(FmapFilePatternStep):
    required_in_path_entities = ["subject"]
    header_str = "Path pattern of the field map image"
    filetype_str = "field map image"
    schema = BaseFmapFileSchema
    filedict = {**FmapFilePatternStep.filedict, "suffix": "fieldmap"}

    def __init__(self, path=""):
        super().__init__(path=path)


class EPIStep(FmapFilePatternStep):
    header_str = "Path pattern of the blip-up blip-down EPI image files"
    required_in_path_entities = ["subject"]

    filetype_str = "blip-up blip-down EPI image"
    schema = EPIFmapFileSchema
    filedict = {**FmapFilePatternStep.filedict, "suffix": "epi"}

    # next_step_type = HasMoreFmapStep


class Magnitude1Step(FmapFilePatternStep):
    header_str = "Path pattern of first set of magnitude image"
    required_in_path_entities = ["subject"]

    filetype_str = "first set of magnitude image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "magnitude1"}
    schema = BaseFmapFileSchema

    # #next_step_type = m_next_step_type


class Magnitude2Step(FmapFilePatternStep):
    header_str = "Path pattern of second set of magnitude image"
    required_in_path_entities = ["subject"]

    filetype_str = "second set of magnitude image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "magnitude2"}
    schema = BaseFmapFileSchema

    # next_step_type = m_next_step_type


class PhaseDiffStep(FmapFilePatternStep):
    header_str = "Path pattern of the phase difference image"
    required_in_path_entities = ["subject"]

    filetype_str = "phase difference image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phasediff"}
    schema = PhaseDiffFmapFileSchema

    # next_step_type = CheckPhaseDiffEchoTimeDiffStep


class Phase1Step(FmapFilePatternStep):
    header_str = "Path pattern of the first set of phase image"
    required_in_path_entities = ["subject"]

    filetype_str = "first set of phase image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phase1"}
    schema = PhaseFmapFileSchema

    # ext_step_type = CheckPhase1EchoTimeStep


class Phase2Step(FmapFilePatternStep):
    header_str = "Path pattern of the second set of phase image"
    required_in_path_entities = ["subject"]

    filetype_str = "second set of phase image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phase2"}
    schema = PhaseFmapFileSchema

    # next_step_type = CheckPhase2EchoTimeStep


# class PhaseTypeStep(BranchStep):
# is_vertical = True
# header_str = "Specify the type of the phase images"
# options = {
# "One phase difference image": PhaseDiffStep,
# "Two phase images": Phase1Step,
# }


# def get_magnitude_steps(m_next_step_type):
# class Magnitude2Step(FilePatternStep):
# filetype_str = "second set of magnitude image"
# filedict = {**filedict, "suffix": "magnitude2"}
# schema = BaseFmapFileSchema

# required_in_path_entities = ["subject"]

# next_step_type = m_next_step_type

# class Magnitude1Step(Magnitude2Step):
# filetype_str = "first set of magnitude image"
# filedict = {**filedict, "suffix": "magnitude1"}

# next_step_type = Magnitude2Step

# class MagnitudeStep(Magnitude1Step):
# filetype_str = "magnitude image"

# next_step_type = m_next_step_type

# class MagnitudeTypeStep(BranchStep):
# is_vertical = True
# header_str = "Specify the type of the magnitude images"
# options = {
# "One magnitude image file": MagnitudeStep,
# "Two magnitude image files": Magnitude1Step,
# }

# return MagnitudeTypeStep


# class CheckPhaseDiffEchoTimeDiffStep(CheckMetadataStep):
# schema = PhaseDiffFmapFileSchema
# key = "echo_time_difference"
# next_step_type = HasMoreFmapStep


# class CheckPhase2EchoTimeStep(CheckMetadataStep):
# schema = PhaseFmapFileSchema
# key = "echo_time"
# next_step_type = HasMoreFmapStep


# class CheckPhase1EchoTimeStep(CheckMetadataStep):
# schema = PhaseFmapFileSchema
# key = "echo_time"
# next_step_type = Phase2Step
####################################################################################


class FilePatternSummaryStep:
    entity_display_aliases: ClassVar[Dict] = entity_display_aliases

    filetype_str: ClassVar[str] = "file"
    filedict: Dict[str, str] = dict()
    schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema

    def __init__(self):
        self.entities = get_schema_entities(self.schema)  # Assumes a function to extract schema entities

        # Assuming ctx and database are accessible here
        self.filepaths = ctx.database.get(**self.filedict)
        self.message = messagefun(
            ctx.database,
            self.filetype_str,
            self.filepaths,
            self.entities,
            entity_display_aliases,  # This should be defined somewhere accessible
        )

    @property
    def get_message(self):
        return self.message

    @property
    def get_summary(self):
        return {"message": self.message, "files": self.filepaths}


class AnatSummaryStep(FilePatternSummaryStep):
    filetype_str = "T1-weighted image"
    filedict = {"datatype": "anat", "suffix": "T1w"}
    schema = T1wFileSchema


class BoldSummaryStep(FilePatternSummaryStep):
    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}
    schema = BoldFileSchema


class FmapSummaryStep(FilePatternSummaryStep):
    filetype_str = "field map image"
    filedict = {"datatype": "fmap"}
    schema = BaseFmapFileSchema


# class FilePatternSummaryStep():
# from ..model.tags import entity_longnames as entity_display_aliases

# entity_display_aliases: ClassVar[Dict] = entity_display_aliases

# filetype_str: ClassVar[str] = "file"
# filedict: Dict[str, str] = dict()
# schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema

# next_step_type: Optional[Type[Step]] = None

# entities = get_schema_entities(self.schema)

# filepaths = ctx.database.get(**self.filedict)
# message = messagefun(
# ctx.database,
# self.filetype_str,
# filepaths,
# entities,
# self.entity_display_aliases,
# )

# def get_message(self):
# return message

# class AnatSummaryStep(FilePatternSummaryStep):
# filetype_str = "T1-weighted image"
# filedict = {"datatype": "anat", "suffix": "T1w"}
# schema = T1wFileSchema

# #FuncSummaryStep = BoldSummaryStep
# #next_step_type = FuncSummaryStep

# class BoldSummaryStep(FilePatternSummaryStep):
# filetype_str = "BOLD image"
# filedict = {"datatype": "func", "suffix": "bold"}
# schema = BoldFileSchema

# #next_step_type = get_post_func_steps(FmapSummaryStep)

# class FmapSummaryStep(FilePatternSummaryStep):
# from ...model.file.fmap import BaseFmapFileSchema

# filetype_str = "field map image"
# filedict = {"datatype": "fmap"}
# bold_filedict = {"datatype": "func", "suffix": "bold"}

# schema = BaseFmapFileSchema

# # next_step_type = FeaturesStep


def messagefun(database, filetype, filepaths, tagnames, entity_display_aliases: dict | None = None):
    entity_display_aliases = dict() if entity_display_aliases is None else entity_display_aliases
    message = ""
    if filepaths is not None:
        message = p.inflect(f"Found {len(filepaths)} {filetype} plural('file', {len(filepaths)})")
        if len(filepaths) > 0:
            n_by_tag = dict()
            for tagname in tagnames:
                tagvalset = database.tagvalset(tagname, filepaths=filepaths)
                if tagvalset is not None:
                    n_by_tag[tagname] = len(tagvalset)
            tagmessages = [
                p.inflect(f"{n} plural('{entity_display_aliases.get(tagname, tagname)}', {n})")
                for tagname, n in n_by_tag.items()
                if n > 0
            ]
            message += " "
            message += "for"
            message += " "
            message += p.join(tagmessages)
    return message


class SetEchoTimeDifferenceModal(DraggableModalScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = "Echo time difference"

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static("Set Echo time difference in seconds"),
                Input(""),
                Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        input_widget = self.query_one(Input)
        if input_widget.value == "":
            self.dismiss(Text("Not Specified!", "on red"))
        else:
            self.dismiss(Text(input_widget.value, "on green"))

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)


class FieldMapFilesPanel(Widget):
    def __init__(self, field_map_type="siemens", step_classes=None, **kwargs) -> None:
        """ """
        super().__init__(**kwargs)
        self.field_map_type = field_map_type
        self.field_map_types_dict = {
            "epi": "EPI (blip-up blip-down)",
            "siemens": "Phase difference and magnitude (used by Siemens scanners)",
            "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
        }
        self.echo_time = 0
        self.step_classes = step_classes

    def compose(self):
        yield Vertical(
            Button("❌", id="delete_button", classes="icon_buttons"),
            *[
                FileItem(
                    delete_button=False,
                    classes="file_patterns",
                    pattern_class=step_class,
                )
                for step_class in self.step_classes
            ],
            classes=self.field_map_type + "_panel",
        )

    def on_mount(self):
        self.query(".{}_panel".format(self.field_map_type)).last(Vertical).border_title = self.field_map_types_dict[
            self.field_map_type
        ]

    def update_echo_time(self, echo_time):
        # self.echo_time = variable
        echo_time_static = self.get_widget_by_id("echo_time")
        if echo_time_static is not None:
            echo_time_static.update(Text("Echo time difference in seconds: ") + echo_time)

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self):
        """Remove the file pattern item."""
        self.remove()

    @on(Button.Pressed, "#edit_button2")
    def _on_edit_button_pressed(self):
        """Remove the file pattern item."""
        self.app.push_screen(SetEchoTimeDifferenceModal(), self.update_echo_time)


class SelectionModal(DraggableModalScreen):
    def __init__(self, options=None, title="", instructions="Select", id: str | None = None, **kwargs) -> None:
        super().__init__(id=id, **kwargs)
        self.title_bar.title = title
        self.instructions = instructions
        RadioButton.BUTTON_INNER = "X"
        self.options = {"a": "A", "b": "B"} if options is None else options
        self.container_to_mount = Container(
            Static(self.instructions, id="title"),
            RadioSet(*[RadioButton(self.options[key]) for key in self.options], id="radio_set"),
            Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
            id="top_container",
        )
        self.choice: str | list = "default_choice??? todo"

    def on_mount(self) -> None:
        """Called when the window is mounted."""
        self.content.mount(self.container_to_mount)

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        self.dismiss(self.choice)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)

    # @on(RadioSet.Changed)
    def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.control.id == "radio_set":
            self.choice = list(self.options.keys())[event.index]


class DoubleSelectionModal(SelectionModal):
    def __init__(self, options=None, title="", instructions=None, id: str | None = None, **kwargs) -> None:
        super().__init__(title=title, id=id, **kwargs)
        self.instructions = instructions
        self.options = options
        self.choice: List[str] = ["default_choice??? todo", "1"]
        self.container_to_mount = Container(
            Static(self.instructions[0], id="title_0"),
            RadioSet(*[RadioButton(self.options[0][key]) for key in self.options[0]], id="radio_set_0"),
            Static(self.instructions[1], id="title_1"),
            RadioSet(*[RadioButton(self.options[1][key]) for key in self.options[1]], id="radio_set_1"),
            Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
            id="top_container",
        )

    def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.control.id == "radio_set_0":
            self.choice[0] = list(self.options[0].keys())[event.index]
        if event.control.id == "radio_set_1":
            self.choice[1] = list(self.options[1].keys())[event.index]


# class EventFileTypeModal(DraggableModalScreen):
# def __init__(self, **kwargs) -> None:
# super().__init__(**kwargs)
# self.title_bar.title = "Field map type specification"
# RadioButton.BUTTON_INNER = "X"
# self.options = {
# "spm": "SPM multiple conditions",
# "fsl": "FSL 3-column",
# "bids": "BIDS TSV",
# }

# def on_mount(self) -> None:
# """Called when the window is mounted."""
# self.content.mount(
# Container(
# Static("Specify the event file type", id="title"),
# RadioSet(*[RadioButton(self.options[key]) for key in self.options]),
# Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
# id="top_container",
# )
# )

# @on(Button.Pressed, "#ok")
# def _on_ok_button_pressed(self):
# self.dismiss(self.choice)

# @on(Button.Pressed, "#cancel")
# def _on_cancel_button_pressed(self):
# self.dismiss(None)

# @on(RadioSet.Changed)
# def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
# self.choice = list(self.options.keys())[event.index]


class DataSummaryLine(Widget):
    def __init__(self, summary=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.summary = {"message": "Found 0 files.", "files": []} if summary is None else summary

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(self.summary["message"], id="feedback"),
            Button("👁", id="show_button", classes="icon_buttons"),
            classes="feedback_container",
        )

    def update_summary(self, summary):
        self.summary = summary
        self.get_widget_by_id("feedback").update(self.summary["message"])
        if len(self.summary["files"]) > 0:
            self.styles.border = ("solid", "green")

    @on(Button.Pressed, "#show_button")
    def _on_show_button_pressed(self):
        self.app.push_screen(ListOfFiles(self.summary))


class DataInput(Widget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    #   self.top_parent = app
    #   self.ctx = ctx
    #   self.available_images = available_images

    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                "If 'on' then just select the BIDS top directory. Otherwise you must select file patterns\
for T1-weighted image, BOLD image and event files.",
                id="description",
            ),
            Horizontal(
                Static("Data in BIDS format", id="bids_format_switch", classes="label"),
                TextSwitch(value=True),
                #        classes="components",
            ),
            id="instructions",
            classes="components",
        )
        yield Grid(
            FileBrowser(path_to="INPUT DATA DIRECTORY", id="data_input_file_browser"),
            id="bids_panel",
            classes="components",
        )
        yield Vertical(
            DataSummaryLine(id="feedback_anat"),
            DataSummaryLine(id="feedback_bold"),
            DataSummaryLine(id="feedback_fmap"),
            id="bids_summary_panel",
            classes="components",
        )
        with VerticalScroll(id="non_bids_panel", classes="components"):
            yield Static(
                "For each file type you need to create a 'path pattern' based on which all files of the particular type will \
be queried. In the pop-up window, choose one particular file (use browse, or copy-paste) and highlight parts \
of the string to be replaced by wildcards. You can also use type hints by starting typing '{' in front of the substring.",
                id="help_top",
            )
            yield Static("Example: We have a particular T1 file and highlight parts with '0001' which represents subjects.")
            yield Static(
                Text(
                    "/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz",
                    spans=[(35, 39, "on red"), (49, 53, "on red")],
                ),
                classes="examples",
            )
            yield Static("After submitting the highlighted parts will be replaced with a particular wildcard type")
            yield Static(
                Text(
                    "/home/tomas/github/ds002785_v2/sub-{subject}/anat/sub-{subject}_T1w.nii.gz",
                    spans=[(35, 44, "on red"), (54, 63, "on red")],
                ),
                classes="examples",
            )

            yield VerticalScroll(Button("Add", id="add_t1_image_button"), id="t1_image_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_bold_image_button"), id="bold_image_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_event_file_button"), id="event_file_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_field_map_button"), id="field_map_panel", classes="non_bids_panels")

    # anatomical/structural data
    # functional data

    def on_mount(self) -> None:
        self.get_widget_by_id("instructions").border_title = "Data format"
        self.get_widget_by_id("bids_panel").border_title = "Path to BIDS directory"
        self.get_widget_by_id("bids_summary_panel").border_title = "Data input file summary"

        self.get_widget_by_id("non_bids_panel").border_title = "Path pattern setup"

        self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"
        self.get_widget_by_id("t1_image_panel").border_title = "T1-weighted image file pattern"
        self.get_widget_by_id("bold_image_panel").border_title = "BOLD image files patterns"
        self.get_widget_by_id("event_file_panel").border_title = "Event files patterns"
        self.get_widget_by_id("field_map_panel").border_title = "Field maps"

    @on(Button.Pressed, "#add_t1_image_button")
    def _add_t1_image(self):
        self.get_widget_by_id("t1_image_panel").mount(FileItem(classes="file_patterns", pattern_class=AnatStep()))
        self.refresh()

    @on(Button.Pressed, "#add_bold_image_button")
    def _add_bold_image(self):
        self.get_widget_by_id("bold_image_panel").mount(FileItem(classes="file_patterns", pattern_class=BoldStep()))
        self.refresh()

    @on(Button.Pressed, "#add_event_file_button")
    def _add_event_file(self):
        def mount_file_item_widget(event_file_type):
            print("qqqqqqqqqqqqqqqqqqqqq", event_file_type)
            events_step_type: Type[EventsStep] | None = None  # Initialize with a default value
            if event_file_type == "bids":
                print("heeeeeeeeeeeeeeeeeeeeeeeeere")
                events_step_type = TsvEventsStep
            elif event_file_type == "fsl":
                print("hhhhhhhhhhhhhhhhe")
                events_step_type = TxtEventsStep
            elif event_file_type == "spm":
                events_step_type = MatEventsStep
            if events_step_type is not None:
                self.get_widget_by_id("event_file_panel").mount(
                    FileItem(classes="file_patterns", pattern_class=events_step_type())
                )
                self.refresh()
            else:
                print("isssssssssssssssssssssss none")

        options = {
            "spm": "SPM multiple conditions",
            "fsl": "FSL 3-column",
            "bids": "BIDS TSV",
        }
        self.app.push_screen(
            SelectionModal(
                title="Event file type specification",
                instructions="Specify the event file type",
                options=options,
                id="event_files_type_modal",
            ),
            mount_file_item_widget,
        )

    @on(Button.Pressed, "#add_field_map_button")
    def _add_field_map_file(self):
        def branch_field_maps(fmap_type):
            if fmap_type == "siemens":
                self.app.push_screen(
                    DoubleSelectionModal(
                        title="Magnitude & phase images",
                        instructions=["Specify the type of the magnitude images", "Specify the type of the phase images"],
                        options=[
                            {
                                "siemens_one_mag_image_file": "One magnitude image file",
                                "siemens_two_mag_image_file": "Two magnitude image file",
                            },
                            {
                                "siemens_one_phase_image_file": "One phase difference image",
                                "siemens_two_phase_image_file": "Two phase images",
                            },
                        ],
                        #  id='magnitude_images_modal'
                    ),
                    self._mount_field_item_group,
                )
            elif fmap_type == "philips":
                self.app.push_screen(
                    SelectionModal(
                        title="Magnitude & phase images",
                        instructions="Specify the type of the magnitude images",
                        options={
                            "philips_one_phase_image_file": "One phase difference image",
                            "philips_two_phase_image_file": "Two phase images",
                        },
                        # id='magnitude_images_modal'
                    ),
                    self._mount_field_item_group,
                )
            elif fmap_type == "epi":
                self.get_widget_by_id("field_map_panel").mount(
                    FieldMapFilesPanel(field_map_type=fmap_type, step_classes=[EPIStep()])
                )
                self.refresh()

        options = {
            "epi": "EPI (blip-up blip-down)",
            "siemens": "Phase difference and magnitude (used by Siemens scanners)",
            "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
        }
        self.app.push_screen(
            SelectionModal(
                title="Field map type specification",
                instructions="Specify type of the field maps",
                options=options,
                id="field_maps_type_modal",
            ),
            branch_field_maps,
            #   self._mount_field_item_group # this was here before
        )

    def _mount_field_item_group(self, field_map_user_choices):
        print("fffffffffffffffffffff", field_map_user_choices)
        # wrap to list, because from the single selection, the choices is just a string and not a list
        field_map_user_choices = (
            field_map_user_choices if isinstance(field_map_user_choices, list) else [field_map_user_choices]
        )
        # get string whether siemens or philips
        field_map_type = field_map_user_choices[0].split("_")[0]
        print("ggggggggggggggggggggggggg", field_map_type)
        # find which classes are needed
        step_classes: List[FilePatternStep] = []

        if any("one_mag_image_file" in s for s in field_map_user_choices):
            step_classes += [Magnitude1Step()]
        elif any("two_mag_image_file" in s for s in field_map_user_choices):
            step_classes += [Magnitude1Step(), Magnitude2Step()]
        if any("one_phase_image_file" in s for s in field_map_user_choices):
            step_classes += [PhaseDiffStep()]
        elif any("two_phase_image_file" in s for s in field_map_user_choices):
            step_classes += [Phase1Step(), Phase2Step()]
        if field_map_type == "philips":
            step_classes += [FieldMapStep()]
        print(
            "ooooooooooooo",
            field_map_user_choices,
            any("one_phase_image_file" in s for s in field_map_user_choices),
            any("two_phase_image_file" in s for s in field_map_user_choices),
        )
        print("1qqqqqqqqqqqqqqqqqssssssssss step_classes", step_classes)
        print("2qqqqqqqqqqqqqqqqqssssssssss step_classes", step_classes)
        if field_map_type is not None:
            self.get_widget_by_id("field_map_panel").mount(
                FieldMapFilesPanel(field_map_type=field_map_type, step_classes=step_classes)
            )
            self.refresh()

    def on_switch_changed(self, message):
        if message.value:
            self.get_widget_by_id("bids_panel").styles.visibility = "visible"
            self.get_widget_by_id("bids_summary_panel").styles.visibility = "visible"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"

        else:
            self.get_widget_by_id("bids_panel").styles.visibility = "hidden"
            self.get_widget_by_id("bids_summary_panel").styles.visibility = "hidden"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "visible"

    def on_file_browser_changed(self, message):
        """Trigger the data read by the Context after a file path is selected."""

        def on_dismiss_this_modal(value):
            self.get_widget_by_id("data_input_file_browser").update_input(None)

        def confirmation(respond: bool):
            print("bla")
            if ~respond:
                self.mount(
                    PathPatternBuilder(
                        path="/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz", classes="components"
                    )
                )

        self.feed_contex_and_extract_available_images(message.selected_path)
        # try:
        # self.feed_contex_and_extract_available_images(message.selected_path)
        # except:  # noqa E722
        # self.app.push_screen(
        # FalseInputWarning(
        # warning_message="The selected data directory seems not be a BIDS directory!",
        # title="Error - Non a bids directory",
        # id="not_bids_dir_warning_modal",
        # classes="error_modal",
        # ),
        # on_dismiss_this_modal,
        # )

    def feed_contex_and_extract_available_images(self, file_path):
        """Feed the Context object with the path to the data fields and extract available images."""
        ctx.put(BidsFileSchema().load({"datatype": "bids", "path": file_path}))

        bold_filedict = {"datatype": "func", "suffix": "bold"}
        filepaths = ctx.database.get(**bold_filedict)
        print("bbbbbbbbbbbbbbbbbbbbbbbbbbbb", file_path, filepaths)
        self.filepaths = list(filepaths)
        assert len(self.filepaths) > 0

        db_entities, db_tags_set = ctx.database.multitagvalset(entities, filepaths=self.filepaths)
        self.app.available_images[db_entities[0]] = sorted(list({t[0] for t in db_tags_set}))

        anat_summary_step = AnatSummaryStep()
        bold_summary_step = BoldSummaryStep()
        fmap_summary_step = FmapSummaryStep()

        self.get_widget_by_id("feedback_anat").update_summary(anat_summary_step.get_summary)
        self.get_widget_by_id("feedback_bold").update_summary(bold_summary_step.get_summary)
        self.get_widget_by_id("feedback_fmap").update_summary(fmap_summary_step.get_summary)

        # at this point, all went well, change border from red to green
        self.get_widget_by_id("data_input_file_browser").styles.border = ("solid", "green")
        # contribute with True to show hidden tabs
        self.app.flags_to_show_tabs["from_input_data_tab"] = True
        self.app.show_hidden_tabs()

    def manually_change_label(self, label):
        """If the input data folder was set by reading an existing json file via the working directory widget,
        the label must be changed externally. This is done in the most top base.
        """
        self.get_widget_by_id("data_input_file_browser").update_input(label)
