# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, fields, post_load

from .tags import TagsSchema


class File:
    def __init__(self, **kwargs):
        self.path = kwargs.get("path")
        self.tags = kwargs.get("tags")

    def __hash__(self):
        return hash((self.path, self.tags))


class FileSchema(Schema):
    path = fields.Str()
    tags = fields.Nested(TagsSchema)

    @post_load
    def make_object(self, data, **kwargs):
        return File(**data)
