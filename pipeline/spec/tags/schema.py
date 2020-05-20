# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow_oneofschema import OneOfSchema

from .base import Tags
from .anat import AnatTagsSchema
from .func import FuncTagsSchema
from .fmap import FmapTagsSchema
from .other import OtherTagsSchema


class TagsWithDatatypeSchema(OneOfSchema):
    type_field = "datatype"
    type_field_remove = False
    type_schemas = {
        "anat": AnatTagsSchema,
        "func": FuncTagsSchema,
        "fmap": FmapTagsSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Tags):
            return obj.datatype
        raise ValueError("Cannot get obj type for TagsSchema")


class TagsSchema(OneOfSchema):
    def _dump(self, obj, *, update_fields=True, **kwargs):
        if obj.datatype is not None:
            return TagsWithDatatypeSchema().dump(obj, many=False, **kwargs)
        else:
            return OtherTagsSchema().dump(obj, many=False, **kwargs)

    def _load(self, data, *, partial=None, unknown=None):
        if "datatype" in data:
            return TagsWithDatatypeSchema().load(
                data, many=False, partial=partial, unknown=unknown
            )
        else:
            return OtherTagsSchema().load(
                data, many=False, partial=partial, unknown=unknown
            )
