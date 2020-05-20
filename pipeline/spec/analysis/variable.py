# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, fields, post_load, validate

from marshmallow_oneofschema import OneOfSchema


class Variable:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.type = kwargs.get("type")
        self.levels = kwargs.get("levels")

    def __hash__(self):
        safelevels = None
        if self.levels is not None:
            safelevels = tuple(self.levels)
        return hash(("variable", self.name, self.type, safelevels))


class BaseVariableSchema(Schema):
    name = fields.Str()

    @post_load
    def make_object(self, data, **kwargs):
        return Variable(**data)


class FirstLevelVariableSchema(BaseVariableSchema):
    type = fields.Str(validate=validate.OneOf(["events"]))


class IdHigherLevelVariableSchema(BaseVariableSchema):
    type = fields.Constant("id")


class ContinuousHigherLevelVariableSchema(BaseVariableSchema):
    type = fields.Constant("continuous")


class CategoricalHigherLevelVariableSchema(BaseVariableSchema):
    type = fields.Constant("categorical")
    levels = fields.List(fields.Str)


class HigherLevelVariableSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "id": IdHigherLevelVariableSchema,
        "continuous": ContinuousHigherLevelVariableSchema,
        "categorical": CategoricalHigherLevelVariableSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Variable):
            return obj.type
        raise Exception("Cannot get obj type for HigherLevelVariable")
