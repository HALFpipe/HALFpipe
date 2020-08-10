# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, ValidationError, fields

from .func import FuncTagsSchema
from ...utils import ravel


def validate_tags(v):
    if isinstance(v, str):
        return
    if isinstance(v, (tuple, list)) and all(isinstance(x, str) for x in ravel(v)):
        return
    raise ValidationError("Need to be either a string or a (nested) list of strings")


ResultdictTagsSchema = Schema.from_dict(
    {
        entity: fields.Raw(validate=validate_tags)
        for entity in [
            *FuncTagsSchema().fields.keys(),
            "stat",
            "setting",
            "feature",
            "model",
            "seed",
            "component",
            "atlas",
            "contrast",
            "desc",
        ]
    }
)
