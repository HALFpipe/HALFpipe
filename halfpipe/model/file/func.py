# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate
from marshmallow_oneofschema import OneOfSchema

from .base import File, BaseFileSchema
from ..tags import BoldTagsSchema, FuncTagsSchema, TxtEventsTagsSchema
from ..metadata import BoldMetadataSchema, EventsMetadataSchema


class BoldFileSchema(BaseFileSchema):
    datatype = fields.Str(default="func", validate=validate.Equal("func"))
    suffix = fields.Str(default="bold", validate=validate.Equal("bold"))
    extension = fields.Str(validate=validate.OneOf([".nii", ".nii.gz"]))

    tags = fields.Nested(BoldTagsSchema, default=dict())
    metadata = fields.Nested(BoldMetadataSchema)


class BaseEventsFileSchema(BaseFileSchema):
    datatype = fields.Str(default="func", validate=validate.Equal("func"))
    suffix = fields.Str(default="events", validate=validate.Equal("events"))

    tags = fields.Nested(FuncTagsSchema, default=dict())


class MatEventsFileSchema(BaseEventsFileSchema):
    extension = fields.Str(validate=validate.OneOf([".mat"]))

    metadata = fields.Nested(EventsMetadataSchema)


class TsvEventsFileSchema(BaseEventsFileSchema):
    extension = fields.Str(validate=validate.OneOf([".tsv"]))

    metadata = fields.Nested(EventsMetadataSchema, default={"units": "seconds"})


class TxtEventsFileSchema(BaseEventsFileSchema):
    extension = fields.Str(validate=validate.OneOf([".txt"]))

    tags = fields.Nested(TxtEventsTagsSchema, default=dict())
    metadata = fields.Nested(EventsMetadataSchema, default={"units": "seconds"})


class EventsFileSchema(OneOfSchema):
    type_field = "extension"
    type_field_remove = False
    type_schemas = {
        ".tsv": TsvEventsFileSchema,
        ".mat": MatEventsFileSchema,
        ".txt": TxtEventsFileSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, File):
            return obj.extension
        raise Exception("Cannot get obj type for EventsFileSchema")


class FuncFileSchema(OneOfSchema):
    type_field = "suffix"
    type_field_remove = False
    type_schemas = {"bold": BoldFileSchema, "events": EventsFileSchema}

    def get_obj_type(self, obj):
        if isinstance(obj, File):
            return obj.suffix
        raise Exception("Cannot get obj type for FuncFileSchema")
