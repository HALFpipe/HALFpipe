# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from enum import Enum

from marshmallow import Schema, fields, post_load, validate
from marshmallow_oneofschema import OneOfSchema

from .contrast import HigherLevelContrastSchema
from .base import Analysis, BaseAnalysisSchema
from .variable import HigherLevelVariableSchema

# HigherLevelAnalysisType = Enum(
#     value="HigherLevelAnalysisType",
#     names=[
#         ("fixed_effects", "fixed_effects"),
#         ("Fixed effects", "fixed_effects"),
#         ("intercept_only", "intercept_only"),
#         ("Intercept-only", "intercept_only"),
#         ("Intercept only", "intercept_only"),
#         ("glm", "glm"),
#         ("GLM", "glm"),
#     ],
# )


class FilterType(Enum):
    mean_fd = "mean_fd"
    fd_gt_0_5 = "fd_gt_0_5"
    group = "group"


class Filter:
    def __init__(self, **kwargs):
        self.type = kwargs.get("type")
        self.cutoff = kwargs.get("cutoff")
        self.variable = kwargs.get("variable")
        self.levels = kwargs.get("levels")
        self.action = kwargs.get("action")


class BaseFilterSchema(Schema):
    @post_load
    def make_object(self, data, **kwargs):
        return Filter(**data)


class BaseCutoffFilterSchema(BaseFilterSchema):
    action = fields.Constant("exclude")
    cutoff = fields.Float()


class MeanFdFilterSchema(BaseCutoffFilterSchema):
    type = fields.Constant(FilterType.mean_fd.value)


class FdGt0_5FilterSchema(BaseCutoffFilterSchema):
    type = fields.Constant(FilterType.fd_gt_0_5.value)


class GroupFilterSchema(BaseFilterSchema):
    action = fields.Str(validate=validate.OneOf(["include", "exclude"]))
    type = fields.Constant(FilterType.group.value)
    variable = fields.Str()
    levels = fields.List(fields.Str)


class FilterSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "mean_fd": MeanFdFilterSchema,
        "fd_gt_0_5": FdGt0_5FilterSchema,
        "group": GroupFilterSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Filter):
            if isinstance(obj.type, FilterType):
                return obj.type.value
            return obj.type
        raise Exception("Cannot get obj type for HigherLevelAnalysis")


class BaseHigherLevelAnalysisSchema(BaseAnalysisSchema):
    level = fields.Constant("higher")
    filter = fields.List(fields.Nested(FilterSchema))
    input = fields.List(fields.Str())


class GLMHigherLevelAnalysisSchema(BaseHigherLevelAnalysisSchema):
    type = fields.Constant("glm")
    across = fields.Constant("subject")
    spreadsheet = fields.Str()
    contrasts = fields.List(fields.Nested(HigherLevelContrastSchema))
    variables = fields.List(fields.Nested(HigherLevelVariableSchema))


class FixedEffectsHigherLevelAnalysisSchema(BaseHigherLevelAnalysisSchema):
    type = fields.Constant("fixed_effects")
    across = fields.Str(
        validate=validate.OneOf(["task", "session", "run", "direction"]),
    )


class InterceptOnlyHigherLevelAnalysisSchema(BaseHigherLevelAnalysisSchema):
    type = fields.Constant("intercept_only")


class HigherLevelAnalysisSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "fixed_effects": FixedEffectsHigherLevelAnalysisSchema,
        "intercept_only": InterceptOnlyHigherLevelAnalysisSchema,
        "glm": GLMHigherLevelAnalysisSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Analysis):
            return obj.type
        raise Exception("Cannot get obj type for HigherLevelAnalysis")
