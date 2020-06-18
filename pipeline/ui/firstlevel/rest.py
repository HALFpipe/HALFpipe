# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from calamities import (
    MultiTextInputView,
    TextInputView,
    TextView,
    SpacerView,
    SingleChoiceInputView,
    FileInputView,
)

from os import path as op
import inflect

from ..pattern import FilePatternStep
from ...spec import (
    File,
    AtlasTagsSchema,
    SeedTagsSchema,
    MapTag,
    MapTagsSchema,
)
from ..utils import forbidden_chars, make_name_suggestion
from ..step import Step
from ...utils import splitext, nvol
from .setting import (
    DoHighPassFilterStep,
    PreSmoothingSettingStep,
    ReHoAndFALFFSettingStep,
)

p = inflect.engine()


class InputSelectStep(Step):
    all_str = "Use all"

    def _make_tagval_strs(self):
        self.tagval_by_str = {}
        for value in self.values:
            dsp_str = f'Use "{value}"'
            self.tagval_by_str[dsp_str] = value
            yield dsp_str

    def setup(self, ctx):
        self.is_first_run = True
        if self.header_str is not None:
            self._append_view(TextView(self.header_str))
        self.values = ctx.database.get_tagvaldict(self.entity)
        self.is_missing = True
        self.choice = None
        if self.values is not None and len(self.values) > 0:
            self.is_missing = False
            self.add_file_str = f"Add {self.filetype_str} file"
            dsp_values = []
            if len(self.values) > 1:
                dsp_values.append(self.all_str)
            dsp_values.extend(self._make_tagval_strs())
            dsp_values.append(self.add_file_str)
            self.input_view = SingleChoiceInputView(dsp_values, isVertical=True)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if not self.is_missing:
            self.choice = self.input_view()
            if self.choice is None:  # was cancelled
                return False
            elif self.choice in self.tagval_by_str:
                setattr(
                    ctx.spec.analyses[-1].tags, self.entity, self.tagval_by_str[self.choice],
                )
            elif self.choice == self.all_str:
                setattr(ctx.spec.analyses[-1].tags, self.entity, None)
            return True
        return self.is_first_run

    def next(self, ctx):
        if (self.is_first_run and self.is_missing) or (
            not self.is_missing and self.choice == self.add_file_str
        ):
            self.is_first_run = False
            return self.add_input_step_type(self.app)(ctx)
        elif self.is_first_run or not self.is_missing:
            self.is_first_run = False
            return self.next_step_type(self.app)(ctx)
        return


class AtlasDoHighPassFilterStep(DoHighPassFilterStep):
    def setup(self, ctx):
        self._append_view(TextView("No smoothing will be performed before feature extraction"))
        self._append_view(SpacerView(1))
        super(AtlasDoHighPassFilterStep, self).setup(ctx)


class AddAtlasStep(FilePatternStep):
    filetype_str = "atlas image"
    tags_dict = {"space": "mni"}
    allowed_entities = ["atlas"]
    ask_if_missing_entities = ["atlas"]
    required_in_pattern_entities = []
    tags_schema = AtlasTagsSchema()
    next_step_type = None
    suggest_file_stem = True


class AtlasSelectStep(InputSelectStep):
    header_str = "Specify atlas"
    entity = "atlas"
    filetype_str = "atlas image"
    next_step_type = AtlasDoHighPassFilterStep
    add_input_step_type = AddAtlasStep


class AddSeedStep(FilePatternStep):
    filetype_str = "binary seed mask image"
    tags_dict = {"space": "mni"}
    allowed_entities = ["seed"]
    ask_if_missing_entities = ["seed"]
    required_in_pattern_entities = []
    tags_schema = SeedTagsSchema()
    next_step_type = None
    suggest_file_stem = True


class SeedSelectStep(InputSelectStep):
    header_str = "Specify seed"
    entity = "seed"
    filetype_str = "seed image"
    next_step_type = PreSmoothingSettingStep
    add_input_step_type = AddSeedStep


AddAtlasStep.next_step_type = AtlasSelectStep
AddSeedStep.next_step_type = SeedSelectStep


def _make_mapfile(filepath, desc, component_names=None):
    _, ext = splitext(filepath)
    if ext[0] == ".":  # remove leading dot
        ext = ext[1:]
    tags_dict = {
        "extension": ext,
        "space": "mni",
        "map": {"desc": desc},
    }
    if component_names is not None:
        tags_dict["map"]["components"] = component_names
    tags_obj = MapTagsSchema().load(tags_dict)
    file_obj = File(path=op.abspath(filepath), tags=tags_obj)
    return file_obj


class MapComponentsStep(Step):
    def __init__(self, app, filepath, nvol, desc):
        super(MapComponentsStep, self).__init__(app)
        self.filepath = filepath
        self.nvol = nvol
        self.desc = desc

    def setup(self, ctx):
        self._append_view(TextView(f"The spatial map has {self.nvol} components"))
        self._append_view(TextView("Specify the spatial map component names"))
        self.options = [f"Component {i+1}" for i in range(self.nvol)]
        suggestion = [
            make_name_suggestion(self.desc, "component", index=i + 1) for i in range(self.nvol)
        ]
        self.input_view = MultiTextInputView(self.options, suggestion)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        res = self.input_view()
        if res is None:  # was cancelled
            return False
        component_names = [res[str(option)] for option in self.options]
        if all(forbidden_chars.search(name) is None for name in component_names):
            file_obj = _make_mapfile(self.filepath, self.desc, component_names)
            ctx.add_file_obj(file_obj)
        return True

    def next(self, ctx):
        return MapSelectStep(self.app)(ctx)


class MapDescStep(Step):
    def __init__(self, app, filepath, nvol):
        super(MapDescStep, self).__init__(app)
        self.filepath = filepath
        self.nvol = nvol
        self.desc, _ = splitext(op.basename(filepath))

    def setup(self, ctx):
        self._append_view(TextView(f"Specify the spatial map name"))
        self.input_view = TextInputView(self.desc)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            self.desc = self.input_view()
            if self.desc is None:  # was cancelled
                return False
            if forbidden_chars.search(self.desc) is None:
                if self.nvol == 1:
                    file_obj = _make_mapfile(self.filepath, self.desc)
                    ctx.add_file_obj(file_obj)
                break
        return True

    def next(self, ctx):
        if self.nvol == 1:
            return MapSelectStep(self.app)(ctx)
        return MapComponentsStep(self.app, self.filepath, self.nvol, self.desc)(ctx)


class AddMapStep(Step):
    filetype_str = "spatial map"

    def setup(self, ctx):
        self._append_view(TextView(f"Specify the path of the {self.filetype_str} file"))
        self.input_view = FileInputView()
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.filepath = self.input_view()
        if self.filepath is None:  # was cancelled
            return False
        self.nvol = nvol(self.filepath)
        assert self.nvol is not None and self.nvol > 0
        return True

    def next(self, ctx):
        return MapDescStep(self.app, filepath=self.filepath, nvol=self.nvol)(ctx)


class MapSelectStep(InputSelectStep):
    header_str = "Specify spatial map file(s)"
    entity = "map"
    filetype_str = "spatial map image"
    next_step_type = PreSmoothingSettingStep
    add_input_step_type = AddMapStep

    def _make_tagval_strs(self):
        self.tagval_by_str = {}
        for value in self.values:
            assert isinstance(value, MapTag)
            dsp_str = f'Use "{value.desc}"'
            if value.components is not None:
                dsp_str += " "
                nvol = len(value.components)
                component_str = p.plural("component", nvol)
                dsp_str += f"({nvol} {component_str})"
            self.tagval_by_str[dsp_str] = value
            yield dsp_str


SeedBasedConnectivityStep = SeedSelectStep
DualRegressionStep = MapSelectStep
AtlasBasedConnectivityStep = AtlasSelectStep
ReHoStep = ReHoAndFALFFSettingStep
FALFFStep = ReHoAndFALFFSettingStep
