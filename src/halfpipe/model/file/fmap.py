# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """

from marshmallow import fields, validate
from marshmallow_oneofschema import OneOfSchema

from ..metadata import PEDirMetadataSchema, PhaseDiffMetadataSchema, TEMetadataSchema
from ..tags import EPIFmapTagsSchema, FmapTagsSchema
from .base import BaseFileSchema, File


class BaseFmapFileSchema(BaseFileSchema):
    datatype = fields.Str(dump_default="fmap", validate=validate.Equal("fmap"))
    suffix = fields.Str(validate=validate.OneOf(["magnitude", "magnitude1", "magnitude2", "fieldmap"]))
    extension = fields.Str(validate=validate.OneOf([".nii", ".nii.gz"]))

    tags = fields.Nested(FmapTagsSchema(), dump_default=dict())
    intended_for = fields.Dict(
        keys=fields.Str(),
        values=fields.List(fields.Str()),
        required=False,
        dump_default=None,
        load_default=None,
        allow_none=True,
    )


class EPIFmapFileSchema(BaseFmapFileSchema):
    suffix = fields.Str(dump_default="epi", validate=validate.Equal("epi"))
    tags = fields.Nested(EPIFmapTagsSchema(), dump_default=dict())
    metadata = fields.Nested(PEDirMetadataSchema())


class PhaseDiffFmapFileSchema(BaseFmapFileSchema):
    suffix = fields.Str(dump_default="phasediff", validate=validate.Equal("phasediff"))
    metadata = fields.Nested(PhaseDiffMetadataSchema())


class PhaseFmapFileSchema(BaseFmapFileSchema):
    suffix = fields.Str(validate=validate.OneOf(["phase1", "phase2"]))
    metadata = fields.Nested(TEMetadataSchema())


class FmapFileSchema(OneOfSchema):
    type_field = "suffix"
    type_field_remove = False
    type_schemas = {
        "phasediff": PhaseDiffFmapFileSchema,
        "phase1": PhaseFmapFileSchema,
        "phase2": PhaseFmapFileSchema,
        "magnitude": BaseFmapFileSchema,
        "magnitude1": BaseFmapFileSchema,
        "magnitude2": BaseFmapFileSchema,
        "fieldmap": BaseFmapFileSchema,
        "epi": EPIFmapFileSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, File):
            return obj.suffix
        raise Exception("Cannot get obj type for FmapFileSchema")
