# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, fields, validate, post_dump
from marshmallow_oneofschema import OneOfSchema

from .filter import FilterSchema


class GlobalSettingsSchema(Schema):
    slice_timing = fields.Boolean(default=False, required=True)
    skull_strip_algorithm = fields.Str(
        validate=validate.OneOf(["none", "auto", "ants", "hdbet"]), default="ants", required=True
    )

    fd_thres = fields.Float(default=0.5, required=True)

    anat_only = fields.Boolean(default=False, required=True)
    write_graph = fields.Boolean(default=False, required=True)

    hires = fields.Boolean(default=False, required=True)
    run_reconall = fields.Boolean(default=False, required=True)
    t2s_coreg = fields.Boolean(default=False, required=True)
    medial_surface_nan = fields.Boolean(default=False, required=True)

    output_spaces = fields.Str(default="MNI152NLin2009cAsym:res-2", required=True)

    bold2t1w_dof = fields.Integer(default=9, required=True, validate=validate.OneOf([6, 9, 12]))
    fmap_bspline = fields.Boolean(default=True, required=True)
    force_syn = fields.Boolean(default=False, required=True, validate=validate.Equal(False))

    longitudinal = fields.Boolean(default=False, required=True)

    regressors_all_comps = fields.Boolean(default=False, required=True)
    regressors_dvars_th = fields.Float(default=1.5, required=True)
    regressors_fd_th = fields.Float(default=0.5, required=True)

    skull_strip_fixed_seed = fields.Boolean(default=False, required=True)
    skull_strip_template = fields.Str(default="OASIS30ANTs", required=True)

    aroma_err_on_warn = fields.Boolean(default=False, required=True)
    aroma_melodic_dim = fields.Int(default=-200, required=True)


class SmoothingSettingSchema(Schema):
    fwhm = fields.Float(validate=validate.Range(min=0.0), required=True)


class GrandMeanScalingSettingSchema(Schema):
    mean = fields.Float(validate=validate.Range(min=0.0), required=True)


class GaussianHighpassSettingSchema(Schema):
    type = fields.Str(default="gaussian", validate=validate.OneOf(["gaussian"]), required=True)
    hp_width = fields.Float(validate=validate.Range(min=0.0))
    lp_width = fields.Float(validate=validate.Range(min=0.0))


class FrequencyBasedBandpassSettingSchema(Schema):
    type = fields.Str(
        default="frequency_based", validate=validate.OneOf(["frequency_based"]), required=True
    )
    low = fields.Float(validate=validate.Range(min=0.0))
    high = fields.Float(validate=validate.Range(min=0.0))


class BandpassFilterSettingSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "gaussian": GaussianHighpassSettingSchema,
        "frequency_based": FrequencyBasedBandpassSettingSchema,
    }

    def get_obj_type(self, obj):
        return obj.get("type")


class SettingSchema(Schema):
    name = fields.Str()

    filters = fields.List(fields.Nested(FilterSchema))

    ica_aroma = fields.Bool(default=True, allow_none=True)  # none is allowed to signify that this step will be skipped
    smoothing = fields.Nested(
        SmoothingSettingSchema, allow_none=True
    )  # none is allowed to signify that this step will be skipped
    grand_mean_scaling = fields.Nested(GrandMeanScalingSettingSchema, allow_none=True)
    bandpass_filter = fields.Nested(BandpassFilterSettingSchema, allow_none=True)
    confounds_removal = fields.List(fields.Str(), default=[])

    output_image = fields.Boolean(default=False)

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}
