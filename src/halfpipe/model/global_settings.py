# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from marshmallow import RAISE, Schema, fields, pre_load, validate


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

    run_aroma = fields.Boolean(dump_default=True)
    aroma_err_on_warn = fields.Boolean(dump_default=False)
    aroma_melodic_dim = fields.Int(dump_default=-200)

    sloppy = fields.Boolean(dump_default=False)

    @pre_load
    def fill_default_values(self, in_data, **_):  # make load_default equal to dump_default
        for k, v in self.fields.items():
            if k not in in_data:
                in_data[k] = v.dump_default
        return in_data
