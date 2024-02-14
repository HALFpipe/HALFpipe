# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from marshmallow import Schema, fields, validate
from marshmallow_oneofschema import OneOfSchema

from .tags import entities


class CutoffFilterSchema(Schema):
    type = fields.Str(dump_default="cutoff", validate=validate.Equal("cutoff"))
    action = fields.Str(dump_default="exclude", validate=validate.OneOf(["exclude"]), required=True)
    field = fields.Str(required=True)
    cutoff = fields.Float(required=True)


class GroupFilterSchema(Schema):
    type = fields.Str(dump_default="group", validate=validate.Equal("group"), required=True)
    action = fields.Str(validate=validate.OneOf(["include", "exclude"]), required=True)
    variable = fields.Str(required=True)
    levels = fields.List(fields.Str(), required=True)


class MissingFilterSchema(Schema):
    type = fields.Str(dump_default="missing", validate=validate.Equal("missing"), required=True)
    action = fields.Str(validate=validate.OneOf(["include", "exclude"]), required=True)
    variable = fields.Str(required=True)


class TagFilterSchema(Schema):
    type = fields.Str(dump_default="tag", validate=validate.Equal("tag"))
    action = fields.Str(validate=validate.OneOf(["include", "exclude"]))
    entity = fields.Str(validate=validate.OneOf([*entities]))
    values = fields.List(fields.Str())


class FilterSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "cutoff": CutoffFilterSchema,
        "group": GroupFilterSchema,
        "missing": MissingFilterSchema,
        "tag": TagFilterSchema,
    }

    def get_obj_type(self, obj):
        return obj.get("type")
