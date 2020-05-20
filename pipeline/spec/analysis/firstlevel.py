# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields
from marshmallow_oneofschema import OneOfSchema

from .contrast import FirstLevelContrastSchema
from .base import Analysis, BaseAnalysisSchema
from ..tags import PreprocessedBoldTagsSchema, SeedTagsSchema, MapTagsSchema, AtlasTagsSchema
from .variable import FirstLevelVariableSchema


class BaseFirstLevelAnalysisSchema(BaseAnalysisSchema):
    level = fields.Constant("first")
    tags = fields.Nested(PreprocessedBoldTagsSchema)


class ImageOutputFirstLevelAnalysisSchema(BaseFirstLevelAnalysisSchema):
    type = fields.Constant("image_output")
    tags = fields.Nested(PreprocessedBoldTagsSchema)


class TaskBasedFirstLevelAnalysisSchema(BaseFirstLevelAnalysisSchema):
    type = fields.Constant("task_based")
    variables = fields.List(fields.Nested(FirstLevelVariableSchema))
    contrasts = fields.List(fields.Nested(FirstLevelContrastSchema))


class SeedBasedConnectivityFirstLevelAnalysis_PreprocessedBoldTagsSchema(
    PreprocessedBoldTagsSchema, SeedTagsSchema
):
    pass


class SeedBasedConnectivityFirstLevelAnalysisSchema(BaseFirstLevelAnalysisSchema):
    type = fields.Constant("seed_based_connectivity")
    tags = fields.Nested(SeedBasedConnectivityFirstLevelAnalysis_PreprocessedBoldTagsSchema)


class DualRegressionFirstLevelAnalysis_PreprocessedBoldTagsSchema(
    PreprocessedBoldTagsSchema, MapTagsSchema
):
    pass


class DualRegressionFirstLevelAnalysisSchema(BaseFirstLevelAnalysisSchema):
    type = fields.Constant("dual_regression")
    tags = fields.Nested(DualRegressionFirstLevelAnalysis_PreprocessedBoldTagsSchema)


class AtlasBasedConnectivityFirstLevelAnalysis_PreprocessedBoldTagsSchema(
    PreprocessedBoldTagsSchema, AtlasTagsSchema
):
    pass


class AtlasBasedConnectivityFirstLevelAnalysisSchema(BaseFirstLevelAnalysisSchema):
    type = fields.Constant("atlas_based_connectivity")
    tags = fields.Nested(AtlasBasedConnectivityFirstLevelAnalysis_PreprocessedBoldTagsSchema)


class ReHoFirstLevelAnalysisSchema(BaseFirstLevelAnalysisSchema):
    type = fields.Constant("reho")


class FALFFFirstLevelAnalysisSchema(BaseFirstLevelAnalysisSchema):
    type = fields.Constant("falff")


class FirstLevelAnalysisSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "image_output": ImageOutputFirstLevelAnalysisSchema,
        "task_based": TaskBasedFirstLevelAnalysisSchema,
        "seed_based_connectivity": SeedBasedConnectivityFirstLevelAnalysisSchema,
        "dual_regression": DualRegressionFirstLevelAnalysisSchema,
        "atlas_based_connectivity": AtlasBasedConnectivityFirstLevelAnalysisSchema,
        "reho": ReHoFirstLevelAnalysisSchema,
        "falff": FALFFFirstLevelAnalysisSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Analysis):
            return obj.type
        raise Exception("Cannot get obj type for FirstLevelAnalysisType")
