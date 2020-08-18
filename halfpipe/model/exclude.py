# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate

from .tags import FuncTagsSchema

rating_indices = {
    "none": -1,
    "good": 0,
    "uncertain": 1,
    "bad": 2,
}


class ExcludeSchema(FuncTagsSchema):
    type = fields.Str()
    rating = fields.Str(validate=validate.OneOf(rating_indices.keys()))
