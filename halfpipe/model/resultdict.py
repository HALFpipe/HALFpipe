# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from pathlib import Path

from marshmallow import Schema, RAISE, fields, ValidationError

from .tags import ResultdictTagsSchema
from ..stats.algorithms import algorithms, modelfit_aliases


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

    *modelfit_aliases.values(),

    # according to https://github.com/bids-standard/bids-specification/blob/derivatives/src/05-derivatives/05-functional-derivatives.md
    "tsnr",
    "alff",
    "falff",
    "reho",
    "timeseries",

    #
    "matrix",
    "regressors",

    # stats outputs
    *(
        output
        for algorithm in algorithms.values()
        for outputs in [algorithm.model_outputs, algorithm.contrast_outputs]
        for output in outputs
    ),
])

ResultdictImagesSchema = Schema.from_dict({
    image_type: fields.Raw(validate=validate_file)
    for image_type in image_types
})


class ResultdictSchema(Schema):
    class Meta:
        unknown = RAISE

    tags = fields.Nested(ResultdictTagsSchema(), dump_default=dict())
    metadata = fields.Dict(keys=fields.Str(), values=fields.Raw(), dump_default=dict())
    images = fields.Nested(ResultdictImagesSchema(), dump_default=dict())
    reports = fields.Dict(
        keys=fields.Str(), values=fields.Raw(validate=validate_file), dump_default=dict()
    )
    vals = fields.Dict(keys=fields.Str(), values=fields.Raw(), dump_default=dict())
