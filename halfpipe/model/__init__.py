# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .spec import SpecSchema, loadspec, savespec
from .tags import BoldTagsSchema, FuncTagsSchema, entities, entity_longnames, resultdict_entities
from .file import (
    File,
    BidsFileSchema,
    AnatFileSchema,
    T1wFileSchema,
    FuncFileSchema,
    BoldFileSchema,
    TxtEventsFileSchema,
    TsvEventsFileSchema,
    MatEventsFileSchema,
    FmapFileSchema,
    PhaseFmapFileSchema,
    PhaseDiffFmapFileSchema,
    EPIFmapFileSchema,
    BaseFmapFileSchema,
    RefFileSchema,
    SpreadsheetFileSchema,
    FileSchema,
)
from .setting import (
    SettingSchema,
    BaseSettingSchema,
    SmoothingSettingSchema,
    BandpassFilterSettingSchema,
    GrandMeanScalingSettingSchema,
)
from .metadata import (
    MetadataSchema,
    templates,
    direction_codes,
    axis_codes,
    space_codes,
    slice_order_strs
)
from .resultdict import ResultdictSchema
from .filter import FilterSchema, GroupFilterSchema, TagFilterSchema, MissingFilterSchema
from .contrast import TContrastSchema, InferredTypeContrastSchema
from .model import (
    Model,
    ModelSchema,
    FixedEffectsModelSchema,
    MixedEffectsModelSchema,
    LinearMixedEffectsModelSchema,
)
from .feature import Feature, FeatureSchema
from .variable import VariableSchema

__all__ = [
    "SpecSchema",
    "loadspec",
    "savespec",
    "BoldTagsSchema",
    "FuncTagsSchema",
    "entities",
    "entity_longnames",
    "resultdict_entities",
    "File",
    "BidsFileSchema",
    "AnatFileSchema",
    "T1wFileSchema",
    "FuncFileSchema",
    "BoldFileSchema",
    "TxtEventsFileSchema",
    "TsvEventsFileSchema",
    "MatEventsFileSchema",
    "FmapFileSchema",
    "PhaseFmapFileSchema",
    "PhaseDiffFmapFileSchema",
    "EPIFmapFileSchema",
    "BaseFmapFileSchema",
    "RefFileSchema",
    "FileSchema",
    "SettingSchema",
    "BaseSettingSchema",
    "SmoothingSettingSchema",
    "BandpassFilterSettingSchema",
    "GrandMeanScalingSettingSchema",
    "MetadataSchema",
    "templates",
    "direction_codes",
    "axis_codes",
    "space_codes",
    "slice_order_strs",
    "ResultdictSchema",
    "FilterSchema",
    "GroupFilterSchema",
    "TagFilterSchema",
    "TContrastSchema",
    "MissingFilterSchema",
    "InferredTypeContrastSchema",
    "Model",
    "ModelSchema",
    "FixedEffectsModelSchema",
    "MixedEffectsModelSchema",
    "LinearMixedEffectsModelSchema",
    "SpreadsheetFileSchema",
    "VariableSchema",
    "Feature",
    "FeatureSchema",
]
