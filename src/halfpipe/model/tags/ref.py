# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from marshmallow import fields

from .base import BaseTagsSchema


class RefTagsSchema(BaseTagsSchema):
    desc = fields.Str()


schemas = [RefTagsSchema]
