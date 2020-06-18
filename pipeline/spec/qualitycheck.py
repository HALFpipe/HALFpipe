# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, Schema, post_load


class QualitycheckExcludeEntry:
    def __init__(self, **kwargs):
        self.subject = kwargs.get("subject")
        self.session = kwargs.get("session")
        self.run = kwargs.get("run")
        self.task = kwargs.get("task")
        self.direction = kwargs.get("direction")

        self.keep = kwargs.get("keep")


class QualitycheckExcludeEntrySchema(Schema):
    subject = fields.Str()
    session = fields.Str()
    run = fields.Str()
    task = fields.Str()
    direction = fields.Str()

    keep = fields.Boolean()

    @post_load
    def make_object(self, data, **kwargs):
        return QualitycheckExcludeEntry(**data)
