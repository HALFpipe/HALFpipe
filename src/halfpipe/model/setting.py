# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from marshmallow import RAISE, Schema, fields, post_dump, pre_load, validate
from marshmallow_oneofschema import OneOfSchema

from .filter import FilterSchema


class GlobalSettingsSchema(Schema):
    class Meta:
        unknown = RAISE
        ordered = True

    dummy_scans = fields.Int(dump_default=0, allow_none=True)

    slice_timing = fields.Boolean(dump_default=False)

    use_bbr = fields.Boolean(dump_default=None, allow_none=True)

    skull_strip_algorithm = fields.Str(validate=validate.OneOf(["none", "auto", "ants", "hdbet"]), dump_default="ants")

    run_mriqc = fields.Boolean(dump_default=False)
    run_fmriprep = fields.Boolean(dump_default=True)
    run_halfpipe = fields.Boolean(dump_default=True)

    fd_thres = fields.Float(dump_default=0.5)

    anat_only = fields.Boolean(dump_default=False)
    write_graph = fields.Boolean(dump_default=False)

    hires = fields.Boolean(dump_default=False)
    run_reconall = fields.Boolean(dump_default=False)
    t2s_coreg = fields.Boolean(dump_default=False)
    medial_surface_nan = fields.Boolean(dump_default=False)

    bold2t1w_dof = fields.Integer(dump_default=9, validate=validate.OneOf([6, 9, 12]))
    fmap_bspline = fields.Boolean(dump_default=True)
    force_syn = fields.Boolean(dump_default=False, validate=validate.Equal(False))

    longitudinal = fields.Boolean(dump_default=False)

    regressors_all_comps = fields.Boolean(dump_default=False)
    regressors_dvars_th = fields.Float(dump_default=1.5)
    regressors_fd_th = fields.Float(dump_default=0.5)

    skull_strip_fixed_seed = fields.Boolean(dump_default=False)
    skull_strip_template = fields.Str(dump_default="OASIS30ANTs")

    aroma_err_on_warn = fields.Boolean(dump_default=False)
    aroma_melodic_dim = fields.Int(dump_default=-200)

    sloppy = fields.Boolean(dump_default=False)

    @pre_load
    def fill_default_values(self, in_data, **_):  # make load_default equal to dump_default
        for k, v in self.fields.items():
            if k not in in_data:
                in_data[k] = v.dump_default
        return in_data


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
    class Meta:
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
