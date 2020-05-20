# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow_oneofschema import OneOfSchema

from .firstlevel import FirstLevelAnalysisSchema
from .higherlevel import HigherLevelAnalysisSchema
from .base import Analysis


class AnalysisSchema(OneOfSchema):
    type_field = "level"
    type_field_remove = False
    type_schemas = {
        "first": FirstLevelAnalysisSchema,
        "higher": HigherLevelAnalysisSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Analysis):
            return obj.level
        raise Exception("Cannot get obj type for Analysis")
