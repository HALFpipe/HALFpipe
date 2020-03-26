# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields
from marshmallow_oneofschema import OneOfSchema

from .contrast import SubjectLevelContrastSchema
from .base import Analysis, BaseAnalysisSchema
from ..tags import BoldTagsSchema
from .variable import SubjectLevelVariableSchema


# SubjectLevelAnalysisType = Enum(
#     value="SubjectLevelAnalysisType",
#     names=[
#         ("task_based", "task_based"),
#         ("Task-based", "task_based"),
#         ("seed_based_connectivity", "seed_based_connectivity"),
#         ("Seed-based connectivity", "seed_based_connectivity"),
#         ("dual_regression", "dual_regression"),
#         ("Dual regression", "dual_regression"),
#         ("atlas_based_connectivity", "atlas_based_connectivity"),
#         ("Atlas-based connectivity matrix", "atlas_based_connectivity"),
#         ("reho", "reho"),
#         ("ReHo", "reho"),
#         ("falff", "falff"),
#         ("fALFF", "falff"),
#     ],
# )


class BaseSubjectLevelAnalysisSchema(BaseAnalysisSchema):
    level = fields.Constant("subject")
    tags = fields.Nested(BoldTagsSchema)  # we only do analyses on bold data


class TaskBasedSubjectLevelAnalysisSchema(BaseSubjectLevelAnalysisSchema):
    type = fields.Constant("task_based")
    variables = fields.List(fields.Nested(SubjectLevelVariableSchema))
    contrasts = fields.List(fields.Nested(SubjectLevelContrastSchema))


class SeedBasedConnectivitySubjectLevelAnalysisSchema(BaseSubjectLevelAnalysisSchema):
    type = fields.Constant("seed_based_connectivity")


class DualRegressionSubjectLevelAnalysisSchema(BaseSubjectLevelAnalysisSchema):
    type = fields.Constant("dual_regression")


class AtlasBasedConnectivitySubjectLevelAnalysisSchema(BaseSubjectLevelAnalysisSchema):
    type = fields.Constant("atlas_based_connectivity")


class ReHoSubjectLevelAnalysisSchema(BaseSubjectLevelAnalysisSchema):
    type = fields.Constant("reho")


class FALFFSubjectLevelAnalysisSchema(BaseSubjectLevelAnalysisSchema):
    type = fields.Constant("falff")


class SubjectLevelAnalysisSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "task_based": TaskBasedSubjectLevelAnalysisSchema,
        "seed_based_connectivity": SeedBasedConnectivitySubjectLevelAnalysisSchema,
        "dual_regression": DualRegressionSubjectLevelAnalysisSchema,
        "atlas_based_connectivity": AtlasBasedConnectivitySubjectLevelAnalysisSchema,
        "reho": ReHoSubjectLevelAnalysisSchema,
        "falff": FALFFSubjectLevelAnalysisSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Analysis):
            return obj.type
        raise Exception("Cannot get obj type for SubjectLevelAnalysisType")
