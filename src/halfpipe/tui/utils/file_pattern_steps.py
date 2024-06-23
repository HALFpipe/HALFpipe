# -*- coding: utf-8 -*-


from typing import Dict, List, Type, Union

from inflection import humanize

from ...ingest.glob import get_entities_in_path, tag_parse
from ...model.file.anat import T1wFileSchema
from ...model.file.base import BaseFileSchema, File
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
from ...utils.path import split_ext
from ..utils.context import ctx
from .meta_data_steps import CheckBoldPhaseEncodingDirectionStep, CheckMetadataStep, CheckPhaseDiffEchoTimeDiffStep

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


def display_str(x):
    if x == "MNI152NLin6Asym":
        return "MNI ICBM 152 non-linear 6th Generation Asymmetric (FSL)"
    elif x == "MNI152NLin2009cAsym":
        return "MNI ICBM 2009c Nonlinear Asymmetric"
    elif x == "slice_encoding_direction":
        return "slice acquisition direction"
    return humanize(x)


##################### CheckMetadataSteps


################ FilePatternSteps


class FilePatternStep:
    entity_display_aliases = entity_display_aliases
    header_str = ""
    ask_if_missing_entities: List[str] = list()
    required_in_path_entities: List[str] = list()

    filetype_str: str = "file"
    filedict: Dict[str, str] = {}
    schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema
    next_step_type: None | type[CheckMetadataStep] = None

    def __init__(self, path="", app=None):
        self.entities = get_schema_entities(self.schema)  # Assumes a function to extract schema entities
        self.path = path
        self.app = app
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
        ctx.database.put(ctx.spec.files[-1])  # we've got all tags, so we can add the fileobj to the index

        if self.next_step_type is not None:
            self.next_step_type(self.app)


class AnatStep(FilePatternStep):
    required_in_path_entities = ["subject"]
    header_str = "T1-weighted image file pattern"
    filetype_str = "T1-weighted image"
    filedict = {"datatype": "anat", "suffix": "T1w"}

    schema = T1wFileSchema

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


# def __init__(self, app=None, path=""):
#    super().__init__(path=path, app=app)


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


class Phase1Step(FmapFilePatternStep):
    header_str = "Path pattern of the first set of phase image"
    required_in_path_entities = ["subject"]

    filetype_str = "first set of phase image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phase1"}
    schema = PhaseFmapFileSchema


# next_step_type = CheckPhase1EchoTimeStep #ok
# next_step_type = CheckBoldPhaseEncodingDirectionStep #ok


class Phase2Step(FmapFilePatternStep):
    header_str = "Path pattern of the second set of phase image"
    required_in_path_entities = ["subject"]

    filetype_str = "second set of phase image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phase2"}
    schema = PhaseFmapFileSchema
    # next_step_type = CheckBoldEffectiveEchoSpacingStep #todo
    # next_step_type = CheckPhase2EchoTimeStep


class PhaseDiffStep(FmapFilePatternStep):
    header_str = "Path pattern of the phase difference image"
    required_in_path_entities = ["subject"]

    filetype_str = "phase difference image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phasediff"}
    schema = PhaseDiffFmapFileSchema

    #   next_step_type = CheckPhaseDiffEchoTimeDiffStep #ok
    #  next_step_type = CheckBoldEffectiveEchoSpacingStep #ok
    # next_step_type = CheckPhase1EchoTimeStep #ok
    next_step_type = CheckPhaseDiffEchoTimeDiffStep  # ok
    # next_step_type = CheckBoldEffectiveEchoSpacingStep #ok


#  next_step_type = CheckBoldPhaseEncodingDirectionStep #ok


class BoldStep(FilePatternStep):
    ask_if_missing_entities = ["task"]
    required_in_path_entities = ["subject"]
    header_str = "BOLD image file pattern"

    schema = BoldFileSchema
    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}

    # def __init__(self, app=None, path=""):
    #     super().__init__(app=app, path=path)

    # next_step_type = CheckBoldEffectiveEchoSpacingStep #ok
    next_step_type = CheckBoldPhaseEncodingDirectionStep  # ok


#     return self.next_step_type(self.app)(ctx)
