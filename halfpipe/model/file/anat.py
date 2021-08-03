# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate
from marshmallow_oneofschema import OneOfSchema

from .base import File, BaseFileSchema
from ..tags import AnatTagsSchema


class T1wFileSchema(BaseFileSchema):
    datatype = fields.Str(dump_default="anat", validate=validate.Equal("anat"))
    suffix = fields.Str(dump_default="T1w", validate=validate.Equal("T1w"))
    extension = fields.Str(validate=validate.OneOf([".nii", ".nii.gz"]))

    tags = fields.Nested(AnatTagsSchema(), dump_default=dict())


class LesionMaskFileSchema(BaseFileSchema):
    datatype = fields.Str(dump_default="anat", validate=validate.Equal("anat"))
    suffix = fields.Str(dump_default="roi", validate=validate.Equal("roi"))
    extension = fields.Str(validate=validate.OneOf([".nii", ".nii.gz"]))

    tags = fields.Nested(AnatTagsSchema(), dump_default=dict())


class AnatFileSchema(OneOfSchema):
    type_field = "suffix"
    type_field_remove = False
    type_schemas = {"T1w": T1wFileSchema, "roi": LesionMaskFileSchema}

    def get_obj_type(self, obj):
        if isinstance(obj, File):
            return obj.suffix
        raise Exception("Cannot get obj type for AnatFileSchema")
