# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from marshmallow import RAISE, Schema, fields, post_load


class File:
    def __init__(
        self,
        path: str,
        datatype: str,
        suffix: str | None = None,
        extension: str | None = None,
        **kwargs,
    ):
        self.path = path
        self.datatype = datatype
        self.suffix = suffix
        self.extension = extension

        self.tags: dict[str, str] = dict()
        self.intended_for: dict | None = None

        self.metadata: dict = dict()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        if not hasattr(other, "path"):
            return False
        return self.path == other.path


class BaseFileSchema(Schema):
    class Meta:
        unknown = RAISE

    path = fields.Str()
    tmplstr = fields.Str()

    @post_load
    def make_object(self, data, **kwargs):
        return File(**data)
