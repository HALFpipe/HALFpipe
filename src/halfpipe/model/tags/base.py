# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from marshmallow import Schema, fields, post_dump
from marshmallow.utils import EXCLUDE


class BaseTagsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    @post_dump(pass_many=False)
    def remove_none_tags(self, data, many):
        return {entity: value for entity, value in data.items() if value is not None}


class SubTagsSchema(BaseTagsSchema):
    sub = fields.Str()


class DirTagsSchema(BaseTagsSchema):
    dir = fields.Str()


class AcqTagsSchema(BaseTagsSchema):
    acq = fields.Str()


class RunTagsSchema(BaseTagsSchema):
    run = fields.Str()


class ScanTagsSchema(SubTagsSchema, RunTagsSchema):
    ses = fields.Str()


schemas = [SubTagsSchema, ScanTagsSchema, AcqTagsSchema, DirTagsSchema]
