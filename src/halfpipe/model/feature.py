# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import TYPE_CHECKING, Any

from marshmallow import Schema, fields, post_dump, post_load, validate
from marshmallow_oneofschema import OneOfSchema

from .contrast import TContrastSchema
from .setting import SmoothingSettingSchema


class Feature:
    def __init__(self, name, type: str, **kwargs) -> None:
        self.name = name
        self.type = type
        # Why would contrasts be defined for every feature?
        self.contrasts: list[dict] | None = None
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __hash__(self):
        return hash(self.name)  # name is unique

    if TYPE_CHECKING:

        def __getattr__(self, attribute: str) -> Any: ...


class BaseFeatureSchema(Schema):
    # how is a name different than type?
    name = fields.Str()

    # whats is a setting?
    setting = fields.Str()

    # why should type be one of these options?
    type = fields.Str(validate=validate.OneOf(["falff", "reho"]))

    @post_load
    def make_object(self, data, **_):
        return Feature(**data)

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        assert many is False
        return {key: value for key, value in data.items() if value is not None}


class BaseTaskBasedFeatureSchema(BaseFeatureSchema):
    type = fields.Str(dump_default="task_based", validate=validate.Equal("task_based"))

    high_pass_filter_cutoff = fields.Float(
        dump_default=125.0,
        load_default=125.0,
        allow_nan=True,
        allow_none=True,
        validate=validate.Range(min=0.0),
    )
    model_serial_correlations = fields.Bool(dump_default=True, load_default=True)

    hrf = fields.Str(
        dump_default="dgamma",
        load_default="dgamma",
        validate=validate.OneOf(["dgamma", "dgamma_with_derivs", "flobs"]),
    )
    conditions = fields.List(fields.Str())


class MultipleTrialTaskBasedFeatureSchema(BaseTaskBasedFeatureSchema):
    estimation = fields.Str(
        load_default="multiple_trial",
        dump_default="multiple_trial",
        validate=validate.Equal("multiple_trial"),
    )
    contrasts = fields.List(fields.Nested(TContrastSchema))


class SingleTrialTaskBasedFeatureSchema(BaseTaskBasedFeatureSchema):
    estimation = fields.Str(
        dump_default="single_trial_least_squares_single",
        validate=validate.OneOf(["single_trial_least_squares_single", "single_trial_least_squares_all"]),
    )


class TaskBasedFeatureSchema(OneOfSchema):
    type_field = "estimation"
    type_field_remove = False
    type_schemas = {
        "multiple_trial": MultipleTrialTaskBasedFeatureSchema,
        "single_trial_least_squares_single": SingleTrialTaskBasedFeatureSchema,
        "single_trial_least_squares_all": SingleTrialTaskBasedFeatureSchema,
    }

    def get_data_type(self, data: Any) -> str:
        type = super().get_data_type(data)
        if type is not None:
            return type
        return "multiple_trial"  # Default value

    def get_obj_type(self, obj):
        if isinstance(obj, Feature):
            return obj.estimation
        raise Exception(f"Cannot get estimation for {obj}")


class SeedBasedConnectivityFeatureSchema(BaseFeatureSchema):
    type = fields.Str(
        dump_default="seed_based_connectivity",
        validate=validate.Equal("seed_based_connectivity"),
    )
    seeds = fields.List(fields.Str())
    min_seed_coverage = fields.Float(dump_default=0.8, validate=validate.Range(min=0.0, max=1.0))


class DualRegressionFeatureSchema(BaseFeatureSchema):
    type = fields.Str(dump_default="dual_regression", validate=validate.Equal("dual_regression"))
    maps = fields.List(fields.Str())


class GroupInformationGuidedICAFeatureSchema(BaseFeatureSchema):
    type = fields.Str(dump_default="gig_ica", validate=validate.Equal("gig_ica"))
    maps = fields.List(fields.Str())


class AtlasBasedConnectivityFeatureSchema(BaseFeatureSchema):
    type = fields.Str(
        dump_default="atlas_based_connectivity",
        validate=validate.Equal("atlas_based_connectivity"),
    )
    atlases = fields.List(fields.Str()) # this gets passed to atlas_names in init wf
    min_region_coverage = fields.Float(dump_default=0.8, validate=validate.Range(min=0.0, max=1.0))


class ReHoFeatureSchema(BaseFeatureSchema):
    smoothing = fields.Nested(
        SmoothingSettingSchema, allow_none=True
    )  # none is allowed to signify that this step will be skipped

    zscore = fields.Bool(dump_default=True, load_default=True)


class FALFFFeatureSchema(ReHoFeatureSchema):
    unfiltered_setting = fields.Str()


class FeatureSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "task_based": TaskBasedFeatureSchema,
        "seed_based_connectivity": SeedBasedConnectivityFeatureSchema,
        "dual_regression": DualRegressionFeatureSchema,
        "gig_ica": GroupInformationGuidedICAFeatureSchema,
        "atlas_based_connectivity": AtlasBasedConnectivityFeatureSchema,
        "reho": ReHoFeatureSchema,
        "falff": FALFFFeatureSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Feature):
            return obj.type
        raise Exception(f"Cannot get type for {obj}")
