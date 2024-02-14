# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict

from marshmallow import Schema, ValidationError, fields

from ...utils.ops import ravel
from .func import FuncTagsSchema


def validate_tags(v):
    if isinstance(v, str):
        return
    if isinstance(v, (tuple, list)) and all(isinstance(x, str) for x in ravel(v)):
        return
    raise ValidationError("Need to be either a string or a (nested) list of strings")


first_level_entities = [
    "feature",
    "setting",
    # seed connectivity
    "seed",
    # dual regression
    "map",
    "component",
    # atlas
    "atlas",
    # task
    "taskcontrast",
]
higher_level_entities = [
    "model",
    "contrast",
    # file descriptors
    "stat",
    "desc",
]
resultdict_entities = [
    *first_level_entities,
    *higher_level_entities,
]

ResultdictTagsSchema = Schema.from_dict(
    OrderedDict(
        [(entity, fields.Raw(validate=validate_tags)) for entity in [*FuncTagsSchema().fields.keys(), *resultdict_entities]]
    )
)
