# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import (
    fields,
    validate,
    Schema,
    post_load,
    post_dump,
    validates_schema,
    ValidationError,
    RAISE,
)
from marshmallow_oneofschema import OneOfSchema

from .contrast import ModelContrastSchema
from .filter import FilterSchema
from ..stats import algorithms


class Model:
    def __init__(self, name, type, **kwargs):
        self.name = name
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __hash__(self):
        return hash(self.name)  # name is unique


class BaseModelSchema(Schema):
    class Meta:
        unknown = RAISE
        ordered = True

    name = fields.Str()

    inputs = fields.List(fields.Str())
    filters = fields.List(fields.Nested(FilterSchema))

    @post_load
    def make_object(self, data, **kwargs):
        return Model(**data)

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}


class FixedEffectsModelSchema(BaseModelSchema):
    type = fields.Str(default="fe", validate=validate.Equal("fe"))
    across = fields.Str(validate=validate.OneOf(["task", "ses", "run", "dir"]))


class MixedEffectsModelSchema(BaseModelSchema):
    type = fields.Str(default="me", validate=validate.Equal("me"))
    across = fields.Str(default="sub", validate=validate.Equal("sub"))

    algorithms = fields.List(
        fields.Str(validate=validate.OneOf(algorithms.keys())),
        default=["flame1", "mcartest", "heterogeneity"],
        missing=["flame1", "mcartest", "heterogeneity"],
    )


class LinearMixedEffectsModelSchema(MixedEffectsModelSchema):
    type = fields.Str(default="lme", validate=validate.Equal("lme"))
    spreadsheet = fields.Str()
    contrasts = fields.List(fields.Nested(ModelContrastSchema))

    @validates_schema
    def validate_contrasts(self, data, **kwargs):
        if "contrasts" not in data:
            return
        names = [c["name"] for c in data["contrasts"] if "name" in c]
        if len(names) > len(set(names)):
            raise ValidationError("Duplicate contrast name")


class ModelSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "fe": FixedEffectsModelSchema,
        "me": MixedEffectsModelSchema,
        "lme": LinearMixedEffectsModelSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Model):
            return obj.type
        raise Exception("Cannot get obj type for Model")
