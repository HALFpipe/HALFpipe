# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate, Schema, post_dump, post_load
from marshmallow_oneofschema import OneOfSchema

from .contrast import TContrastSchema
from .setting import SmoothingSettingSchema


class Feature:
    def __init__(self, **kwargs):
        assert "name" in kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __hash__(self):
        return hash(self.name)  # name is unique


class BaseFeatureSchema(Schema):
    name = fields.Str()

    setting = fields.Str()

    type = fields.Str(validate=validate.OneOf(["falff", "reho"]))

    @post_load
    def make_object(self, data, **kwargs):
        return Feature(**data)

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}


class TaskBasedFeatureSchema(BaseFeatureSchema):
    type = fields.Str(default="task_based", validate=validate.Equal("task_based"))

    conditions = fields.List(fields.Str())
    contrasts = fields.List(fields.Nested(TContrastSchema))

    high_pass_filter_cutoff = fields.Float(default=125.0, validate=validate.Range(min=0.0))

    orthogonalize = fields.Dict(keys=fields.Str(), values=fields.List(fields.Str()), default=dict())
    hrf_derivs = fields.Bool(default=False)


class SeedBasedConnectivityFeatureSchema(BaseFeatureSchema):
    type = fields.Str(
        default="seed_based_connectivity", validate=validate.Equal("seed_based_connectivity")
    )
    seeds = fields.List(fields.Str())
    min_seed_coverage = fields.Float(default=0.8, validate=validate.Range(min=0.0, max=1.0))


class DualRegressionFeatureSchema(BaseFeatureSchema):
    type = fields.Str(default="dual_regression", validate=validate.Equal("dual_regression"))
    maps = fields.List(fields.Str())


class AtlasBasedConnectivityFeatureSchema(BaseFeatureSchema):
    type = fields.Str(
        default="atlas_based_connectivity", validate=validate.Equal("atlas_based_connectivity")
    )
    atlases = fields.List(fields.Str())
    min_region_coverage = fields.Float(default=0.8, validate=validate.Range(min=0.0, max=1.0))


class ReHoFeatureSchema(BaseFeatureSchema):
    smoothing = fields.Nested(
        SmoothingSettingSchema, allow_none=True
    )  # none is allowed to signify that this step will be skipped


class FALFFFeatureSchema(ReHoFeatureSchema):
    unfiltered_setting = fields.Str()


class FeatureSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "task_based": TaskBasedFeatureSchema,
        "seed_based_connectivity": SeedBasedConnectivityFeatureSchema,
        "dual_regression": DualRegressionFeatureSchema,
        "atlas_based_connectivity": AtlasBasedConnectivityFeatureSchema,
        "reho": ReHoFeatureSchema,
        "falff": FALFFFeatureSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Feature):
            return obj.type
        raise Exception("Cannot get obj type for FeatureType")
