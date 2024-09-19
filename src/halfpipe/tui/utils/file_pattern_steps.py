# -*- coding: utf-8 -*-


from typing import Dict, List, Type, Union

from inflection import humanize

from ...ingest.glob import tag_parse
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
from ...model.file.ref import RefFileSchema
from ...model.file.schema import FileSchema
from ...model.tags import entities
from ...model.tags import entity_longnames as entity_display_aliases
from ...model.utils import get_schema_entities
from ...utils.path import split_ext
from ..utils.context import ctx
from .meta_data_steps import (
    CheckMetadataStep,
    CheckPhase1EchoTimeStep,
    CheckPhase2EchoTimeStep,
    CheckPhaseDiffEchoTimeDiffStep,
    CheckRepetitionTimeStep,
    CheckSpaceStep,
)

entity_colors = {
    "sub": "red",
    "ses": "green",
    "run": "magenta",
    "task": "cyan",
    "dir": "yellow",
    "condition": "orange",
    "desc": "blue",  # Changed to blue for uniqueness
    "acq": "purple",  # Changed to purple for uniqueness
    "echo": "brown",  # Changed to brown for uniqueness
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

    def __init__(self, path="", app=None, callback=None, callback_message=None, id_key=""):
        self.entities = get_schema_entities(self.schema)  # Assumes a function to extract schema entities
        self.path = path
        self.app = app
        # setup
        self.fileobj: File | None = None

        self.callback = callback
        self.callback_message = callback_message  # if callback_message is not None else {self.filetype_str: []}
        # if callback_message is not None:
        #     self.callback_message.update({self.filetype_str: []})

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
        print("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiid key", self.id_key)
        # ctx.cache[self.id_key]["files"][self.filetype_str] = self.fileobj
        ctx.cache[self.id_key]["files"] = self.fileobj  # type: ignore[assignment]

        print("heeeeeeeeeeeeeeeeeeeeeeereeeeeeeeeeeeeeeeeeeeeeeeeee", self.next_step_type)
        if self.next_step_type is not None:
            self.next_step_instance = self.next_step_type(
                app=self.app,
                callback=self.callback,
                callback_message=self.callback_message,
                id_key=self.id_key,
                sub_id_key=self.filetype_str,
            )
            self.next_step_instance.run()


class AnatStep(FilePatternStep):
    required_in_path_entities = ["subject"]
    header_str = "T1-weighted image file pattern"
    filetype_str = "T1-weighted image"
    filedict = {"datatype": "anat", "suffix": "T1w"}

    schema = T1wFileSchema

    def __init__(self, path=""):
        super().__init__(path=path)


# def find_bold_file_paths():
#     bold_file_paths = ctx.database.get(datatype="func", suffix="bold")
#
#     if bold_file_paths is None:
#         raise ValueError("No BOLD files in database")
#
#     #  filters = ctx.spec.settings[-1].get("filters")
#     filters = None
#     bold_file_paths = set(bold_file_paths)
#
#     if filters is not None:
#         bold_file_paths = ctx.database.applyfilters(bold_file_paths, filters)
#
#     return bold_file_paths


class EventsStep(FilePatternStep):
    header_str = "Event file pattern"
    required_in_path_entities: List[str] = list()

    ask_if_missing_entities: List[str] = list()
    filedict = {"datatype": "func", "suffix": "events"}
    filetype_str = "event"

    # def __init__(self, path=""):
    # super().__init__(path=path)

    # # setup
    # bold_file_paths = find_bold_file_paths()

    # taskset = ctx.database.tagvalset("task", filepaths=bold_file_paths)
    # if taskset is None:
    # taskset = set()
    # self.taskset = taskset

    # if len(self.taskset) > 1:
    # self.required_in_path_entities = ["task"]
    # #        super(EventsStep, self).setup(ctx)

    # # next
    # if len(self.taskset) == 1:
    # assert isinstance(self.fileobj, File)
    # if self.fileobj.tags.get("task") is None:
    # if "task" not in get_entities_in_path(self.fileobj.path):
    # (self.fileobj.tags["task"],) = self.taskset

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


class Magnitude1Step(FmapFilePatternStep):
    header_str = "Path pattern of first set of magnitude image"
    required_in_path_entities = ["subject"]

    filetype_str = "first set of magnitude image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "magnitude1"}
    schema = BaseFmapFileSchema


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

    next_step_type = CheckPhase1EchoTimeStep


class Phase2Step(FmapFilePatternStep):
    header_str = "Path pattern of the second set of phase image"
    required_in_path_entities = ["subject"]

    filetype_str = "second set of phase image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phase2"}
    schema = PhaseFmapFileSchema

    next_step_type = CheckPhase2EchoTimeStep


class PhaseDiffStep(FmapFilePatternStep):
    header_str = "Path pattern of the phase difference image"
    required_in_path_entities = ["subject"]

    filetype_str = "phase difference image"
    filedict = {**FmapFilePatternStep.filedict, "suffix": "phasediff"}
    schema = PhaseDiffFmapFileSchema

    next_step_type = CheckPhaseDiffEchoTimeDiffStep


class BoldStep(FilePatternStep):
    ask_if_missing_entities = ["task"]
    required_in_path_entities = ["subject"]
    header_str = "BOLD image file pattern"

    schema = BoldFileSchema
    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}

    next_step_type = CheckRepetitionTimeStep


class AddAtlasImageStep(FilePatternStep):
    suffix, featurefield, dsp_str = "atlas", "atlases", "atlas"
    filetype_str = f"{dsp_str} image"
    filedict = {"datatype": "ref", "suffix": suffix}
    entity_display_aliases = {"desc": suffix}

    schema = RefFileSchema

    ask_if_missing_entities = ["desc"]
    required_in_path_entities = []

    next_step_type = CheckSpaceStep


class AddSpatialMapStep(FilePatternStep):
    suffix, featurefield, dsp_str = "map", "maps", "spatial map"
    filetype_str = f"{dsp_str} image"
    filedict = {"datatype": "ref", "suffix": suffix}
    entity_display_aliases = {"desc": suffix}

    schema = RefFileSchema

    ask_if_missing_entities = ["desc"]
    required_in_path_entities = []


class AddBinarySeedMapStep(FilePatternStep):
    suffix, featurefield, dsp_str = "seed", "seeds", "binary seed mask"
    filetype_str = f"{dsp_str} image"
    filedict = {"datatype": "ref", "suffix": suffix}
    entity_display_aliases = {"desc": suffix}

    schema = RefFileSchema

    ask_if_missing_entities = ["desc"]
    required_in_path_entities = []


###############################################################################################################################
# def find_bold_file_paths():
#     bold_file_paths = ctx.database.get(datatype="func", suffix="bold")
#
#     if bold_file_paths is None:
#         raise ValueError("No BOLD files in database")
#
#     filters = ctx.spec.settings[-1].get("filters")
#     bold_file_paths = set(bold_file_paths)
#
#     if filters is not None:
#         bold_file_paths = ctx.database.applyfilters(bold_file_paths, filters)
#
#     return bold_file_paths
#
#
# def get_conditions():
#     bold_file_paths = find_bold_file_paths()
#
#     conditions: list[str] = list()
#     seen = set()
#     for bold_file_path in bold_file_paths:
#         event_file_paths = collect_events(ctx.database, bold_file_path)
#
#         if event_file_paths is None:
#             continue
#
#         if event_file_paths in seen:
#             continue
#
#         cf = ConditionFile(data=event_file_paths)
#         for condition in cf.conditions:  # maintain order
#             if condition not in conditions:
#                 conditions.append(condition)
#
#         seen.add(event_file_paths)
#
#     ctx.spec.features[-1].conditions = conditions


# # start with this one, we assume that the "images" are already extracted
# # This should be now modal and the choice should trigger one of the EventsSteps which essentially leads to another modal,
# # the path pattern builder. From that the conditions should be then extracted by the ConditionsSelectStep
# class EventsTypeStep:
#     header_str = "Specify the event file type"
#     options = {
#         MatEventsStep: "SPM multiple conditions",
#         TxtEventsStep: "FSL 3-column",
#         TsvEventsStep: "BIDS TSV",
#     }
#
#     def __init__(self, path="", app=None, callback=None, callback_message=None, id_key=""):
#         self.app = app
#
#     # self.force_run = force_run
#
#     def setup(self):
#         #  self.is_first_run = True
#         self.should_run = False
#
#         # try to load conditions if not available
#         get_conditions(ctx)
#
#         if (
#             not hasattr(ctx.spec.features[-1], "conditions")
#             or ctx.spec.features[-1].conditions is None
#             or len(ctx.spec.features[-1].conditions) == 0
#             #       or self.force_run
#         ):  # check if load was successful
#             self.should_run = True
#
#     def run(self):
#         self.setup()
#         self.run2()
#         print("i am hereeeeee")
#
#     @work
#     async def run2(self):
#         if self.should_run:
#             self.app.push_screen_wait(
#                 SelectionModal(title="Event file type", instructions=header_str, options=self.options),
#                 self.next,
#             )
#         else:
#             self.next(None)
#         #  return super(EventsTypeStep, self).run(ctx)
#
#     #   return self.is_first_run
#
#     def next(self, events_type_step):
#         if self.should_run:  # if it is neccessery to run the modal
#             print("run the EventsTypeStep!!!!!!!!!!!!")
#             # events_type_step_instance = events_type_step()
#             # events_type_step_instance.run()
#         # return super(EventsTypeStep, self).next(ctx)
#         else:  # if we can go directly to the condition extraction
#             #  if self.is_first_run:
#             #      self.is_first_run = False
#             print("run the ConditionsSelectStep!!!!!!!!!!!!")
#             # conditions_select_step_instance = ConditionsSelectStep(self.app)
#             # conditions_select_step_instance.run()
#             # else:
#             #    return


###########################
# for consistency, somehow adapt this:
# it is done differently in new TUI somewhere else, i think!

#
# class SettingFilterStep:
#     def _format_tag(self, tag):
#         return f'"{tag}"'
#
#     def setup(self):
#         self.is_first_run = True
#         self.choice = None
#
#         bold_filedict = {"datatype": "func", "suffix": "bold"}
#         filepaths = ctx.database.get(**bold_filedict)
#         self.filepaths = list(filepaths)
#         assert len(self.filepaths) > 0
#
#         db_entities, db_tags_set = ctx.database.multitagvalset(entities, filepaths=self.filepaths)
#
#         self.entities = []
#         options = []
#         self.tagval_by_str = {}
#         values = []
#         for entity, tagvals_list in zip(db_entities, zip(*db_tags_set, strict=False), strict=False):
#             if entity == "sub":
#                 continue
#
#             tagvals_set = set(tagvals_list)
#             if 1 < len(tagvals_set) < 16:
#                 self.entities.append(entity)
#
#                 entity_str = entity
#                 if entity_str in entity_display_aliases:
#                     entity_str = entity_display_aliases[entity_str]
#                 entity_str = humanize(entity_str)
#                 options.append((entity_str, entity_colors[entity]))
#
#                 if None in tagvals_set:
#                     tagvals_set.remove(None)
#
#                 tagvals = sorted(list(tagvals_set))
#
#                 row = [f'"{tagval}"' for tagval in tagvals]
#                 values.append(row)
#
#                 self.tagval_by_str.update(dict(zip(row, tagvals, strict=False)))
#
#         print("oooooooooooooooooooooooooooptions vvvvvvvvvvvvalues", options, values)
#         self.choice = values[0]
#         if len(options) == 0:
#             self.should_run = False
#         else:
#             self.should_run = True
#
#     #      self._append_view(TextView("Specify images to use"))
#
#     #     self.input_view = MultiMultipleChoiceInputView(options, values, checked=values)
#
#     #    self._append_view(self.input_view)
#     #    self._append_view(SpacerView(1))
#
#     def run(self):
#         self.setup()
#         print("self.should_runself.should_runself.should_runself.should_run", self.should_run)
#         # if not self.should_run:
#         # return self.is_first_run
#         # else:
#         # #self.choice = self.input_view()
#         # #if self.choice is None:
#         # #    return False
#         # return True
#         self.next()
#
#     def next(self):
#         self.choice = [{'"anticipation"': True, '"emomatching"': True, '"gstroop"': True, '"workingmemory"': True}]
#         print(
#             "elf.choiceelf.choiceelf.choice",
#             self.choice,
#         )
#         print("ctx.spec.settingsctx.spec.settingsctx.spec.settings", ctx.spec.settings)
#         if self.choice is not None:
#             filter_schema = FilterSchema()
#
#             # if ctx.spec.settings[-1].get("filters") is None:
#             #     ctx.spec.settings[-1]["filters"] = []
#
#             for entity, checked in zip(self.entities, self.choice, strict=False):
#                 print("entity, checkedentity, checked entity, checked:::::::::::::::", entity, checked)
#
#                 if all(checked.values()):
#                     continue
#                 assert any(checked.values())
#
#                 selected_tagvals = []
#                 for tag_str, is_selected in checked.items():
#                     if is_selected:
#                         selected_tagvals.append(self.tagval_by_str[tag_str])
#                 print("eeeeeeeeeeeeeeeeeeeeeentity entity selected_tagvals,:::", entity, ":::", selected_tagvals)
#                 _filter = filter_schema.load(
#                     {
#                         "type": "tag",
#                         "action": "include",
#                         "entity": entity,
#                         "values": selected_tagvals,
#                     }
#                 )
#                 #     ctx.spec.settings[-1]["filters"].append(_filter)
#                 print("filterfilterfilterfilterfilterfilter", _filter)
#
#         if self.should_run or self.is_first_run:
#             print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa i am here")
#             self.is_first_run = False
#             # return next_step_type(self.app)(ctx)
#             events_type_instance = EventsTypeStep()
#             events_type_instance.run()
