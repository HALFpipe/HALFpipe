# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""


from marshmallow import Schema, fields, validate
from marshmallow_oneofschema import OneOfSchema


class BaseVariableSchema(Schema):
    name = fields.Str()
    type = fields.Str(validate=validate.OneOf(["id", "continuous"]))


class CategoricalVariableSchema(BaseVariableSchema):
    type = fields.Str(
        dump_default="categorical", validate=validate.Equal("categorical")
    )
    levels = fields.List(fields.Str)


class VariableSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "id": BaseVariableSchema,
        "continuous": BaseVariableSchema,
        "categorical": CategoricalVariableSchema,
    }

    def get_obj_type(self, obj):
        return obj.get("type")
