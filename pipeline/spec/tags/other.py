# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, fields, post_load, validate

from marshmallow_oneofschema import OneOfSchema

from .base import BaseSchema


class MapTag:
    def __init__(self, **kwargs):
        self.components = kwargs.get("components")
        self.desc = kwargs.get("desc")

    def __hash__(self):
        return hash((*self.components, self.desc))

    def __eq__(self, other):
        return self.desc == other.desc


class MapTagSchema(Schema):
    desc = fields.Str()
    components = fields.List(fields.Str)

    @post_load
    def make_object(self, data, **kwargs):
        return MapTag(**data)


class BaseOtherTagsSchema(BaseSchema):
    extension = fields.Str(validate=validate.OneOf(["nii", "nii.gz"]))
    space = fields.Str(validate=validate.OneOf(["mni"]))


class AtlasTagsSchema(BaseOtherTagsSchema):
    atlas = fields.Str()


class SeedTagsSchema(BaseOtherTagsSchema):
    seed = fields.Str()


class MapTagsSchema(BaseOtherTagsSchema):
    map = fields.Nested(MapTagSchema)


class OtherTagsSchema(OneOfSchema):
    def _dump(self, obj, *, update_fields=True, **kwargs):
        if obj.atlas is not None:
            return AtlasTagsSchema().dump(obj, many=False, **kwargs)
        elif obj.seed is not None:
            return SeedTagsSchema().dump(obj, many=False, **kwargs)
        elif obj.map is not None:
            return MapTagsSchema().dump(obj, many=False, **kwargs)
        else:
            return BaseOtherTagsSchema().dump(obj, many=False, **kwargs)

    def _load(self, data, *, partial=None, unknown=None):
        if "atlas" in data:
            return AtlasTagsSchema().load(data, many=False, partial=partial, unknown=unknown)
        elif "seed" in data:
            return SeedTagsSchema().load(data, many=False, partial=partial, unknown=unknown)
        elif "map" in data:
            return MapTagsSchema().load(data, many=False, partial=partial, unknown=unknown)
        else:
            return BaseOtherTagsSchema().load(data, many=False, partial=partial, unknown=unknown)
