# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import RAISE, Schema, fields

from .tags import ResultdictTagsSchema


class ResultdictSchema(Schema):
    class Meta:
        unknown = RAISE

    tags = fields.Nested(ResultdictTagsSchema(), dump_default=dict())
    metadata = fields.Dict(keys=fields.Str(), values=fields.Raw(), dump_default=dict())
    images = fields.Dict(keys=fields.Str(), values=fields.Raw(), dump_default=dict())
    reports = fields.Dict(keys=fields.Str(), dump_default=dict())
    vals = fields.Dict(keys=fields.Str(), values=fields.Raw(), dump_default=dict())
