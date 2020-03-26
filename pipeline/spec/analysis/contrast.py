# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, fields, post_load
from marshmallow_oneofschema import OneOfSchema


class Contrast:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.type = kwargs.get("type")
        self.values = kwargs.get("values")
        self.variable = kwargs.get("variable")


class BaseContrastSchema(Schema):
    @post_load
    def make_object(self, data, **kwargs):
        return Contrast(**data)


class SubjectLevelContrastSchema(BaseContrastSchema):
    type = fields.Constant("t")
    name = fields.Str()
    values = fields.Dict(keys=fields.Str(), values=fields.Float())


class TContrastSchema(BaseContrastSchema):
    type = fields.Constant("t")
    name = fields.Str()
    variable = fields.List(fields.Str())
    values = fields.Dict(keys=fields.Str(), values=fields.Float())


class InferredTypeContrastSchema(BaseContrastSchema):
    type = fields.Constant("infer")
    variable = fields.List(fields.Str())


class HigherLevelContrastSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {"t": TContrastSchema, "infer": InferredTypeContrastSchema}

    def get_obj_type(self, obj):
        if isinstance(obj, Contrast):
            return obj.type
        raise Exception("Cannot get obj type for ContrastSchema")
