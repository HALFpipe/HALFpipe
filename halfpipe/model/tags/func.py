# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields

from .base import ScanTagsSchema, DirTagsSchema


class FuncTagsSchema(ScanTagsSchema, DirTagsSchema):
    task = fields.Str()


class BoldTagsSchema(FuncTagsSchema):
    echo = fields.Str()


class TxtEventsTagsSchema(FuncTagsSchema):
    condition = fields.Str()


__all__ = [FuncTagsSchema, BoldTagsSchema, TxtEventsTagsSchema]
