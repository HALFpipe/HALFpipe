# -*- coding: utf-8 -*-


from typing import Dict, List, Type, Union

from ...ingest.glob import get_entities_in_path, tag_glob, tag_parse
from ...logging import logger
from ...model.file.anat import T1wFileSchema, T1wMaskFileSchema
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
from ...model.file.ref import RefFileSchema
from ...model.file.schema import FileSchema
from ...model.tags import entities
from ...model.tags import entity_longnames as entity_display_aliases
from ...model.utils import get_schema_entities
from ...utils.path import split_ext
from ..data_analyzers.context import ctx
from ..help_functions import find_bold_file_paths
from ..standards import entity_colors
from .meta_data_steps import (
    CheckMetadataStep,
    CheckPhase1EchoTimeStep,
    CheckPhase2EchoTimeStep,
    CheckPhaseDiffEchoTime1Step,
    CheckRepetitionTimeStep,
    CheckSpaceStep,
)


class FilePatternStep:
    """
    Base class for defining file pattern steps in a data processing pipeline.

    This class provides a framework for handling different types of files,
    checking their extensions, parsing their paths, and pushing them to a
    context object. It also manages the required and optional entities in
    the file paths and defines the next steps in the pipeline.

    Attributes
    ----------
    entity_display_aliases : dict
        A dictionary mapping entity names to their display aliases.
    header_str : str
        A string describing the file pattern step.
    ask_if_missing_entities : list[str]
        A list of entities that should be asked for if missing in the path.
    required_in_path_entities : list[str]
        A list of entities that are required to be present in the path.
    filetype_str : str
        A string describing the type of file being handled.
    filedict : dict[str, str]
        A dictionary containing file type information.
    schema : Union[Type[BaseFileSchema], Type[FileSchema]]
        The schema used to validate the file.
    next_step_type : None | type[CheckMetadataStep]
        The type of the next step in the pipeline.
    schema_entities : list[str]
        List of entities extracted from the schema.

    """

    entity_display_aliases = entity_display_aliases
    header_str = ""
    ask_if_missing_entities: List[str] = list()
    required_in_path_entities: List[str] = list()

    filetype_str: str = "file"
    filedict: Dict[str, str] = {}
    schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema
    next_step_type: None | type[CheckMetadataStep] = None

    def __init__(self, path="", app=None, callback=None, callback_message=None, id_key=""):
        """
        Initializes the FilePatternStep.

        Parameters
        ----------
        path : str, optional
            The path to the file, by default ""
        app : Any, optional
            The application object, by default None. This we need in order to push
            the modal to the correct screen.
        callback : Callable, optional
            A callback function, by default None. This in principle  would not be needed
            if we use workers for every step type class. Something to think about.
        callback_message : Any, optional
            A message for the callback, by default None
        id_key : str, optional
            The id key for the context, by default ""
        """
        self.entities = get_schema_entities(self.schema)  # Assumes a function to extract schema entities
        self.path = path
        self.app = app
        # setup
        self.fileobj: File | None = None

        self.callback = callback
        self.callback_message = callback_message  # if callback_message is not None else {self.filetype_str: []}

        schema_entities = get_schema_entities(self.schema)
        schema_entities = [entity for entity in reversed(entities) if entity in schema_entities]  # keep order
        # convert to display
        self.schema_entities = [
            (self.entity_display_aliases[entity] if entity in self.entity_display_aliases else entity)
            for entity in schema_entities
        ]
        self.id_key = id_key

        # need original entities for this
        self.entity_colors_list = [entity_colors[entity] for entity in schema_entities]

        self.required_entities = [
            *self.ask_if_missing_entities,
            *self.required_in_path_entities,
        ]

    def _transform_extension(self, ext):
        """
        Transforms the file extension.

        Parameters
        ----------
        ext : str
            The file extension.

        Returns
        -------
        str
            The transformed file extension.
        """
        return ext

    @property
    def get_entities(self):
        """
        Gets the schema entities.

        Returns
        -------
        list[str]
            The list of schema entities.
        """
        return self.schema_entities

    @property
    def get_entity_colors_list(self):
        """
        Gets the entity colors list.

        Returns
        -------
        list[str]
            The list of entity colors.
        """
        return self.entity_colors_list

    @property
    def get_required_entities(self):
        """
        Gets the required entities.

        Returns
        -------
        list[str]
            The list of required entities.
        """
        return self.required_entities

    def check_extension(self, path):
        """
        Checks the file extension against the schema.

        Parameters
        ----------
        path : str
            The path to the file.
        """
        filedict = {**self.filedict, "path": path, "tags": {}}
        _, ext = split_ext(path)
        filedict["extension"] = self._transform_extension(ext)
        self.schema().load(filedict)

    def run_before_next_step(self):
        pass

    async def push_path_to_context_obj(self, path):
        """
        Pushes the file path to the context object.

        This method parses the file path, creates a file object, adds it to
        the context's specification and database, and then proceeds to the
        next step in the pipeline if defined.

        Parameters
        ----------
        path : str
            The path to the file.
        """
        # run
        inv = {alias: entity for entity, alias in self.entity_display_aliases.items()}

        i = 0
        _path = ""
        logger.debug(f"UI->FilePatternStep.run_before_next_step(): get_entities_in_path(path) {get_entities_in_path(path)}")
        for match in tag_parse.finditer(path):
            logger.debug(f"UI->FilePatternStep.run_before_next_step(): match: {match}")
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

        # find what tasks will be given based on the uses task placeholder
        tagglobres = list(tag_glob(self.fileobj.path))
        task_set = set()
        for _filepath, tagdict in tagglobres:
            task = tagdict.get("task", None)
            if task is not None:
                task_set.add(task)

        logger.info(f"UI->FilePatternStep.run_before_next_step-> ctx.available_images:{ctx.available_images}")
        logger.info(f"UI->FilePatternStep.run_before_next_step-> found tasks:{task_set}")

        # next
        ctx.spec.files.append(self.fileobj)
        ctx.database.put(ctx.spec.files[-1])  # we've got all tags, so we can add the fileobj to the index
        ctx.cache[self.id_key]["files"] = self.fileobj  # type: ignore[assignment]

        self.run_before_next_step()

        if self.next_step_type is not None:
            self.next_step_instance = self.next_step_type(
                app=self.app,
                callback=self.callback,
                callback_message=self.callback_message,
                id_key=self.id_key,
                sub_id_key=self.filetype_str,
            )
            await self.next_step_instance.run()
        else:
            pass


class AnatStep(FilePatternStep):
    """
    File pattern step for handling anatomical (T1-weighted) images.

    This class extends FilePatternStep to specifically handle T1-weighted
    anatomical images. It defines the required entities, header string,
    file type string, file dictionary, and schema for T1-weighted images.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[T1wFileSchema]
        The schema for T1-weighted images.
    """

    required_in_path_entities = ["subject"]
    header_str = "T1-weighted image file pattern"
    filetype_str = "T1-weighted image"
    filedict = {"datatype": "anat", "suffix": "T1w"}

    schema = T1wFileSchema


class AnatMaskStep(FilePatternStep):
    """
    File pattern step for handling anatomical (T1-weighted) images.

    This class extends FilePatternStep to specifically handle T1-weighted
    anatomical images. It defines the required entities, header string,
    file type string, file dictionary, and schema for T1-weighted images.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[T1wFileSchema]
        The schema for T1-weighted images.
    """

    required_in_path_entities = ["subject"]
    header_str = "Lesion mask file pattern"
    filetype_str = "Lesion mask"
    filedict = {"datatype": "anat", "suffix": "roi"}

    schema = T1wMaskFileSchema


class EventsStep(FilePatternStep):
    """
    Base file pattern step for handling event files.

    This class extends FilePatternStep to handle event files. It defines
    the header string, required entities, file dictionary, and file type
    string for event files.

    Attributes
    ----------
    header_str : str
        The header string for event files.
    filedict : dict[str, str]
        The file dictionary for event files.
    """

    def __init__(self, *args, **kwargs):
        bold_file_paths = find_bold_file_paths()

        taskset = ctx.database.tagvalset("task", filepaths=bold_file_paths)
        if taskset is None:
            taskset = set()
        self.taskset = taskset
        logger.info(f"UI->EventsStep->init taskset: {taskset}")

        if len(self.taskset) > 1:
            self.required_in_path_entities = ["task"]
        super().__init__(*args, **kwargs)

    def run_before_next_step(self):
        if len(self.taskset) == 1:
            assert isinstance(self.fileobj, File)

            if self.fileobj.tags.get("task") is None:
                if "task" not in get_entities_in_path(self.fileobj.path):
                    (self.fileobj.tags["task"],) = self.taskset

    header_str = " Input stimulus onset files"  # Event file pattern
    required_in_path_entities: List[str] = list()

    ask_if_missing_entities: List[str] = list()
    filedict = {"datatype": "func", "suffix": "events"}
    filetype_str = "event"

    def _transform_extension(self, ext):
        raise NotImplementedError()


class MatEventsStep(EventsStep):
    """
    File pattern step for handling MATLAB (.mat) event files.

    This class extends EventsStep to specifically handle MATLAB event files.
    It defines the schema for MATLAB event files and overrides the
    `_transform_extension` method to ensure the correct file extension.

    Attributes
    ----------
    schema : Type[MatEventsFileSchema]
        The schema for MATLAB event files.

    """

    schema = MatEventsFileSchema

    def _transform_extension(self, ext):
        assert ext == ".mat"
        return ext


# next_step_type = CheckUnitsStep


class TxtEventsStep(EventsStep):
    """
    File pattern step for handling text (.txt) event files.

    This class extends EventsStep to specifically handle text event files.
    It defines the schema for text event files, requires the 'condition'
    entity in the path, and overrides the `_transform_extension` method.

    Attributes
    ----------
    schema : Type[TxtEventsFileSchema]
        The schema for text event files.
    required_in_path_entities : list[str]
        List of entities required in the path, including 'condition'.
    """

    schema = TxtEventsFileSchema
    required_in_path_entities = ["condition"]

    def _transform_extension(self, _):
        return ".txt"


class TsvEventsStep(EventsStep):
    """
    File pattern step for handling TSV (.tsv) event files.

    This class extends EventsStep to specifically handle TSV event files.
    It defines the schema for TSV event files and overrides the
    `_transform_extension` method.

    Attributes
    ----------
    schema : Type[TsvEventsFileSchema]
        The schema for TSV event files.
    """

    schema = TsvEventsFileSchema

    def _transform_extension(self, _):
        return ".tsv"


class FmapFilePatternStep(FilePatternStep):
    """
    File pattern step for handling TSV (.tsv) event files.

    This class extends EventsStep to specifically handle TSV event files.
    It defines the schema for TSV event files and overrides the
    `_transform_extension` method.

    Attributes
    ----------
    schema : Type[TsvEventsFileSchema]
        The schema for TSV event files.
    """

    bold_filedict = {"datatype": "func", "suffix": "bold"}
    filetype_str = "field map image"
    filetype_str = filetype_str
    filedict = {"datatype": "fmap"}


class FieldMapStep(FmapFilePatternStep):
    """
    File pattern step for handling general field map files.

    This class extends FmapFilePatternStep to specifically handle general
    field map files. It defines the required entities, header string,
    file type string, file dictionary, and schema for general field map files.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[BaseFmapFileSchema]
        The schema for general field map files.
    """

    required_in_path_entities = ["subject"]
    header_str = "Path pattern of the field map image"
    filetype_str = "field map image"
    schema = BaseFmapFileSchema
    filedict = {**FmapFilePatternStep.filedict, "suffix": "fieldmap"}

    def __init__(self, path=""):
        super().__init__(path=path)


class EPIStep(FmapFilePatternStep):
    """
    File pattern step for handling EPI field map files.

    This class extends FmapFilePatternStep to specifically handle EPI
    field map files. It defines the required entities, header string,
    file type string, file dictionary, and schema for EPI field map files.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[EPIFmapFileSchema]
        The schema for EPI field map files.
    """

    header_str = "Path pattern of the blip-up blip-down EPI image files"
    required_in_path_entities = ["subject"]

    filetype_str = "blip-up blip-down EPI image"
    schema = EPIFmapFileSchema
    filedict = {**FmapFilePatternStep.filedict, "suffix": "epi"}


class Magnitude1Step(FmapFilePatternStep):
    """
    File pattern step for handling the first set of magnitude images.

    This class extends FmapFilePatternStep to specifically handle the first
    set of magnitude images. It defines the required entities, header string,
    file type string, file dictionary, and schema for the first set of
    magnitude images.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    """

    header_str = "Path pattern of first set of magnitude image"
    required_in_path_entities = ["subject"]

    filetype_str = "first set of magnitude image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "magnitude1"}
    schema = BaseFmapFileSchema


class Magnitude2Step(FmapFilePatternStep):
    """
    File pattern step for handling the second set of magnitude images.

    This class extends FmapFilePatternStep to specifically handle the second
    set of magnitude images. It defines the required entities, header string,
    file type string, file dictionary, and schema for the second set of
    magnitude images.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    """

    header_str = "Path pattern of second set of magnitude image"
    required_in_path_entities = ["subject"]

    filetype_str = "second set of magnitude image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "magnitude2"}
    schema = BaseFmapFileSchema

    # next_step_type = m_next_step_type


class Phase1Step(FmapFilePatternStep):
    """
    File pattern step for handling the first set of phase images.

    This class extends FmapFilePatternStep to specifically handle the first
    set of phase images. It defines the required entities, header string,
    file type string, file dictionary, schema, and the next step for the
    first set of phase images.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[PhaseFmapFileSchema]
        The schema for the first set of phase images.
    next_step_type : Type[CheckPhase1EchoTimeStep]
        The type of the next step in the pipeline.
    """

    header_str = "Path pattern of the first set of phase image"
    required_in_path_entities = ["subject"]

    filetype_str = "first set of phase image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phase1"}
    schema = PhaseFmapFileSchema

    next_step_type = CheckPhase1EchoTimeStep


class Phase2Step(FmapFilePatternStep):
    """
    File pattern step for handling the second set of phase images.

    This class extends FmapFilePatternStep to specifically handle the second
    set of phase images. It defines the required entities, header string,
    file type string, file dictionary, schema, and the next step for the
    second set of phase images.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[PhaseFmapFileSchema]
        The schema for the second set of phase images.
    next_step_type : Type[CheckPhase2EchoTimeStep]
        The type of the next step in the pipeline.
    """

    header_str = "Path pattern of the second set of phase image"
    required_in_path_entities = ["subject"]

    filetype_str = "second set of phase image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phase2"}
    schema = PhaseFmapFileSchema

    next_step_type = CheckPhase2EchoTimeStep


class PhaseDiffStep(FmapFilePatternStep):
    """
    File pattern step for handling phase difference images.

    This class extends FmapFilePatternStep to specifically handle phase
    difference images. It defines the required entities, header string,
    file type string, file dictionary, schema, and the next step for phase
    difference images.

    Attributes
    ----------
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[PhaseDiffFmapFileSchema]
        The schema for phase difference images.
    next_step_type : Type[CheckPhaseDiffEchoTimeDiffStep]
        The type of the next step in the pipeline.
    """

    header_str = "Path pattern of the phase difference image"
    required_in_path_entities = ["subject"]

    filetype_str = "phase difference image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phasediff"}
    schema = PhaseDiffFmapFileSchema

    next_step_type = CheckPhaseDiffEchoTime1Step


class BoldStep(FilePatternStep):
    """
    File pattern step for handling BOLD images.

    This class extends FilePatternStep to specifically handle BOLD images.
    It defines the required and optional entities, header string, file type
    string, file dictionary, schema, and the next step for BOLD images.

    Attributes
    ----------
    ask_if_missing_entities : list[str]
        List of entities to ask for if missing, including 'task'.
    required_in_path_entities : list[str]
        List of entities required in the path, including 'subject'.
    schema : Type[BoldFileSchema]
        The schema for BOLD images.
    next_step_type : Type[CheckRepetitionTimeStep]
        The type of the next step in the pipeline.
    """

    ask_if_missing_entities = ["task"]
    required_in_path_entities = ["subject"]
    header_str = "BOLD image file pattern"

    schema = BoldFileSchema
    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}

    next_step_type = CheckRepetitionTimeStep


class AddAtlasImageStep(FilePatternStep):
    """
    File pattern step for adding atlas images.

    This class extends FilePatternStep to specifically handle atlas images.
    It defines the suffix, feature field, display string, file type string,
    file dictionary, entity display aliases, schema, required and optional
    entities, and the next step for atlas images.

    Attributes
    ----------
    ask_if_missing_entities : list[str]
        List of entities to ask for if missing, including 'desc'.
    required_in_path_entities : list[str]
        List of entities required in the path, empty in this case.
    schema : Type[RefFileSchema]
        The schema for atlas images.
    next_step_type : Type[CheckSpaceStep]
        The type of the next step in the pipeline.
    """

    suffix, featurefield, dsp_str = "atlas", "atlases", "atlas"
    filetype_str = f"{dsp_str} image"
    filedict = {"datatype": "ref", "suffix": suffix}
    entity_display_aliases = {"desc": suffix}

    schema = RefFileSchema

    ask_if_missing_entities = [suffix]
    required_in_path_entities = []

    next_step_type = CheckSpaceStep


class AddSpatialMapStep(FilePatternStep):
    """
    File pattern step for adding spatial map images.

    This class extends FilePatternStep to specifically handle spatial map
    images. It defines the suffix, feature field, display string, file type
    string, file dictionary, entity display aliases, schema, required and
    optional entities, and the next step for spatial map images.

    Attributes
    ----------
    ask_if_missing_entities : list[str]
        List of entities to ask for if missing, including 'desc'.
    required_in_path_entities : list[str]
        List of entities required in the path, empty in this case.
    schema : Type[RefFileSchema]
        The schema for spatial map images.
    next_step_type : Type[CheckSpaceStep]
        The type of the next step in the pipeline.
    """

    suffix, featurefield, dsp_str = "map", "maps", "spatial map"
    filetype_str = f"{dsp_str} image"
    filedict = {"datatype": "ref", "suffix": suffix}
    entity_display_aliases = {"desc": suffix}

    schema = RefFileSchema

    ask_if_missing_entities = [suffix]
    required_in_path_entities = []

    next_step_type = CheckSpaceStep


class AddBinarySeedMapStep(FilePatternStep):
    """
    File pattern step for adding binary seed mask images.

    This class extends FilePatternStep to specifically handle binary seed mask
    images. It defines the suffix, feature field, display string, file type
    string, file dictionary, entity display aliases, schema, required and
    optional entities, and the next step for binary seed mask images.

    Attributes
    ----------
    ask_if_missing_entities : list[str]
        List of entities to ask for if missing, including 'desc'.
    required_in_path_entities : list[str]
        List of entities required in the path, empty in this case.
    schema : Type[RefFileSchema]
        The schema for binary seed mask images.
    next_step_type : Type[CheckSpaceStep]
        The type of the next step in the pipeline.
    """

    suffix, featurefield, dsp_str = "seed", "seeds", "binary seed mask"
    filetype_str = f"{dsp_str} image"
    filedict = {"datatype": "ref", "suffix": suffix}
    entity_display_aliases = {"desc": suffix}

    schema = RefFileSchema

    ask_if_missing_entities = [suffix]
    required_in_path_entities = []

    next_step_type = CheckSpaceStep
