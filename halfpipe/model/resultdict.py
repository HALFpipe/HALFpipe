# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from pathlib import Path

from marshmallow import Schema, RAISE, fields, ValidationError

from .metadata import ResultdictMetadataSchema
from .tags import ResultdictTagsSchema
from ..stats.algorithms import algorithms


def validate_file(v):
    def is_ok(x):
        return isinstance(x, str) and Path(x).is_file()

    if is_ok(v):
        return
    if isinstance(v, (tuple, list)) and all(is_ok(x) for x in v):
        return
    raise ValidationError("Need to be either a file or a list of files")


image_types = frozenset([
    # according to https://fmriprep.org/en/stable/outputs.html
    "bold",
    "mask",

    # according to https://github.com/poldracklab/fitlins/blob/0.6.2/fitlins/workflows/base.py
    "effect",
    "variance",
    "z",
    "dof",

    # according to https://github.com/bids-standard/bids-specification/blob/derivatives/src/05-derivatives/05-functional-derivatives.md
    "tsnr",
    "alff",
    "falff",
    "reho",
    "timeseries",

    #
    "matrix",
    "regressors",

    #
    *[
        output
        for algorithm in algorithms.values()
        for output in algorithm.outputs
    ],
])

ResultdictImagesSchema = Schema.from_dict({
    image_type: fields.Raw(validate=validate_file)
    for image_type in image_types
})


def validate_val(v):
    if isinstance(v, float) or isinstance(v, str):
        return
    if isinstance(v, (tuple, list)) and all(isinstance(x, str) for x in v):
        return
    raise ValidationError("Need to be either a float, a string or a list of strings")


class ResultdictSchema(Schema):
    class Meta:
        unknown = RAISE

    tags = fields.Nested(ResultdictTagsSchema(), default=dict())
    metadata = fields.Nested(ResultdictMetadataSchema(), default=dict())
    images = fields.Nested(ResultdictImagesSchema(), default=dict())
    reports = fields.Dict(
        keys=fields.Str(), values=fields.Raw(validate=validate_file), default=dict()
    )
    vals = fields.Dict(keys=fields.Str(), values=fields.Raw(validate=validate_val), default=dict())
