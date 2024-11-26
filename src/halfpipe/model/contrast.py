# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """

from marshmallow import Schema, fields, validate
from marshmallow_oneofschema.one_of_schema import OneOfSchema


class TContrastSchema(Schema):
    type = fields.Str(dump_default="t", validate=validate.Equal("t"))
    name = fields.Str()
    variable = fields.List(fields.Str())
    values = fields.Dict(keys=fields.Str(), values=fields.Float())


class InferredTypeContrastSchema(Schema):
    type = fields.Str(dump_default="infer", validate=validate.Equal("infer"))
    variable = fields.List(fields.Str())


class ModelContrastSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {"t": TContrastSchema, "infer": InferredTypeContrastSchema}

    def get_obj_type(self, obj):
        return obj.get("type")
