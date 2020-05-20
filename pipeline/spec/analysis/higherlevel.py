# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, fields, post_load, validate
from marshmallow_oneofschema import OneOfSchema

from .contrast import HigherLevelContrastSchema
from .base import Analysis, BaseAnalysisSchema
from .variable import HigherLevelVariableSchema


class Filter:
    def __init__(self, **kwargs):
        self.type = kwargs.get("type")
        self.action = kwargs.get("action")
        self.cutoff = kwargs.get("cutoff")
        self.variable = kwargs.get("variable")
        self.levels = kwargs.get("levels")

    def __hash__(self):
        safelevels = None
        if self.levels is not None:
            safelevels = tuple(self.levels)
        return hash(
            ("filter", self.type, self.action, self.cutoff, self.variable, safelevels,)
        )


class BaseFilterSchema(Schema):
    @post_load
    def make_object(self, data, **kwargs):
        return Filter(**data)


class BaseCutoffFilterSchema(BaseFilterSchema):
    action = fields.Constant("exclude")
    cutoff = fields.Float()


class MeanFdFilterSchema(BaseCutoffFilterSchema):
    type = fields.Constant("mean_fd")


class FdGt0_5FilterSchema(BaseCutoffFilterSchema):
    type = fields.Constant("fd_gt_0_5")


class GroupFilterSchema(BaseFilterSchema):
    action = fields.Str(validate=validate.OneOf(["include", "exclude"]))
    type = fields.Constant("group")
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
            return obj.type
        raise Exception("Cannot get obj type for Filter")


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
    across = fields.Str(validate=validate.OneOf(["task", "session", "run", "direction"]),)


class InterceptOnlyHigherLevelAnalysisSchema(BaseHigherLevelAnalysisSchema):
    type = fields.Constant("intercept_only")
    across = fields.Constant("subject")


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
