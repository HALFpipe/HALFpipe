# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate

from marshmallow_oneofschema import OneOfSchema

from ..direction import phase_encoding_direction_values
from .base import BaseSchema, Tags
from .derivative import (
    SmoothedTagSchema,
    BandPassFilteredTagSchema,
    ConfoundsRemovedTagSchema,
)

study_entities = ["task", "session", "run", "direction"]
bold_entities = study_entities + ["subject"]


class BaseFuncTagsSchema(BaseSchema):
    datatype = fields.Constant("func")

    subject = fields.Str()
    session = fields.Str()
    run = fields.Str()
    task = fields.Str()
    direction = fields.Str()


class BaseEventsTagsSchema(BaseFuncTagsSchema):
    suffix = fields.Constant("events")


class MatEventsTagsSchema(BaseEventsTagsSchema):
    extension = fields.Constant("mat")


class TsvEventsTagsSchema(BaseEventsTagsSchema):
    extension = fields.Constant("tsv")


class TxtEventsTagsSchema(BaseEventsTagsSchema):
    extension = fields.Constant("txt")
    condition = fields.Str()


class EventsTagsSchema(OneOfSchema):
    type_field = "extension"
    type_field_remove = False
    type_schemas = {
        "tsv": TsvEventsTagsSchema,
        "txt": TxtEventsTagsSchema,
        "mat": MatEventsTagsSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Tags):
            return obj.extension
        raise Exception("Cannot get obj type for EventsTagsSchema")


class BoldTagsSchema(BaseFuncTagsSchema):
    suffix = fields.Constant("bold")

    extension = fields.Str(validate=validate.OneOf(["nii", "nii.gz"]))

    repetition_time = fields.Float()

    effective_echo_spacing = fields.Float()
    phase_encoding_direction = fields.Str(
        validate=validate.OneOf(phase_encoding_direction_values)
    )


class PreprocessedBoldTagsSchema(BoldTagsSchema):
    space = fields.Str(validate=validate.OneOf(["mni"]))
    smoothed = fields.Nested(SmoothedTagSchema)
    band_pass_filtered = fields.Nested(BandPassFilteredTagSchema)
    confounds_removed = fields.Nested(ConfoundsRemovedTagSchema)


class FuncTagsSchema(OneOfSchema):
    type_field = "suffix"
    type_field_remove = False
    type_schemas = {"events": EventsTagsSchema, "bold": BoldTagsSchema}

    def get_obj_type(self, obj):
        if isinstance(obj, Tags):
            return obj.suffix
        raise Exception("Cannot get obj type for FuncTagsSchema")
