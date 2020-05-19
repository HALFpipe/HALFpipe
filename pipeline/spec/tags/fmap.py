# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate

from marshmallow_oneofschema import OneOfSchema

from ..direction import phase_encoding_direction_values
from .base import BaseSchema, Tags


class BaseFmapTagsSchema(BaseSchema):
    datatype = fields.Constant("fmap")

    extension = fields.Str(validate=validate.OneOf(["nii", "nii.gz"]))

    subject = fields.Str()
    session = fields.Str()
    run = fields.Str()
    task = fields.Str()


class PEPOLARTagsSchema(BaseFmapTagsSchema):
    suffix = fields.Constant("epi")

    phase_encoding_direction = fields.Str(validate=validate.OneOf(phase_encoding_direction_values))


class PhaseDifferenceTagsSchema(BaseFmapTagsSchema):
    suffix = fields.Constant("phasediff")

    echo_time_difference = fields.Float()


class Phase1TagsSchema(BaseFmapTagsSchema):
    suffix = fields.Constant("phase1")
    echo_time = fields.Float()


class Phase2TagsSchema(BaseFmapTagsSchema):
    suffix = fields.Constant("phase2")
    echo_time = fields.Float()


class Magnitude1TagsSchema(BaseFmapTagsSchema):
    suffix = fields.Constant("magnitude1")


class Magnitude2TagsSchema(BaseFmapTagsSchema):
    suffix = fields.Constant("magnitude2")


class FieldMapTagsSchema(BaseFmapTagsSchema):
    suffix = fields.Constant("fieldmap")


class FmapTagsSchema(OneOfSchema):
    type_field = "suffix"
    type_field_remove = False
    type_schemas = {
        "phasediff": PhaseDifferenceTagsSchema,
        "phase1": Phase1TagsSchema,
        "phase2": Phase2TagsSchema,
        "magnitude1": Magnitude1TagsSchema,
        "magnitude2": Magnitude2TagsSchema,
        "fieldmap": FieldMapTagsSchema,
        "epi": PEPOLARTagsSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Tags):
            return obj.suffix
        raise Exception("Cannot get obj type for FuncTagsSchema")
