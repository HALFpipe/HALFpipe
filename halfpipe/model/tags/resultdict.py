# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from collections import OrderedDict

from marshmallow import Schema, ValidationError, fields

from .func import FuncTagsSchema
from ...utils import ravel


def validate_tags(v):
    if isinstance(v, str):
        return
    if isinstance(v, (tuple, list)) and all(isinstance(x, str) for x in ravel(v)):
        return
    raise ValidationError("Need to be either a string or a (nested) list of strings")


resultdict_entities = [
    # levels of analysis
    "model",
    "feature",
    "setting",
    # types of features
    "seed",
    "map",
    "atlas",
    "taskcontrast",
    # file descriptors
    "component",
    "contrast",
    "stat",
    "desc",
]

ResultdictTagsSchema = Schema.from_dict(
    OrderedDict([
        (entity, fields.Raw(validate=validate_tags))
        for entity in [*FuncTagsSchema().fields.keys(), *resultdict_entities]
    ])
)
