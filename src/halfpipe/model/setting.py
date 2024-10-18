# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from marshmallow import RAISE, Schema, fields, post_dump, validate
from marshmallow_oneofschema.one_of_schema import OneOfSchema

from .filter import FilterSchema


class SmoothingSettingSchema(Schema):
    fwhm = fields.Float(validate=validate.Range(min=0.0), required=True)


class GrandMeanScalingSettingSchema(Schema):
    mean = fields.Float(validate=validate.Range(min=0.0), required=True)


class GaussianHighpassSettingSchema(Schema):
    type = fields.Str(dump_default="gaussian", validate=validate.OneOf(["gaussian"]), required=True)
    hp_width = fields.Float(validate=validate.Range(min=0.0), allow_none=True)
    lp_width = fields.Float(validate=validate.Range(min=0.0), allow_none=True)


class FrequencyBasedBandpassSettingSchema(Schema):
    type = fields.Str(
        dump_default="frequency_based",
        validate=validate.OneOf(["frequency_based"]),
        required=True,
    )
    low = fields.Float(validate=validate.Range(min=0.0), allow_none=True)
    high = fields.Float(validate=validate.Range(min=0.0), allow_none=True)


class BandpassFilterSettingSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "gaussian": GaussianHighpassSettingSchema,
        "frequency_based": FrequencyBasedBandpassSettingSchema,
    }

    def get_obj_type(self, obj):
        return obj.get("type")


class BaseSettingSchema(Schema):
    class Meta(Schema.Meta):
        unknown = RAISE
        ordered = True

    ica_aroma = fields.Bool(allow_none=True)  # none is allowed to signify that this step will be skipped
    smoothing = fields.Nested(
        SmoothingSettingSchema, allow_none=True
    )  # none is allowed to signify that this step will be skipped
    grand_mean_scaling = fields.Nested(GrandMeanScalingSettingSchema, allow_none=True)
    bandpass_filter = fields.Nested(BandpassFilterSettingSchema, allow_none=True)
    confounds_removal = fields.List(fields.Str())


class SettingSchema(BaseSettingSchema):
    name = fields.Str()

    filters = fields.List(fields.Nested(FilterSchema))

    output_image = fields.Boolean(dump_default=False)

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}
