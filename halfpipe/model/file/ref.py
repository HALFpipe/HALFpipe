# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate

from .base import BaseFileSchema
from ..tags import RefTagsSchema
from ..metadata import RefMetadataSchema


class RefFileSchema(BaseFileSchema):
    datatype = fields.Str(default="ref", validate=validate.OneOf(["ref"]))
    suffix = fields.Str(default="seed", validate=validate.OneOf(["seed", "map", "atlas"]))
    extension = fields.Str(validate=validate.OneOf([".nii", ".nii.gz"]))
    tags = fields.Nested(RefTagsSchema(), default=dict())
    metadata = fields.Nested(RefMetadataSchema())
