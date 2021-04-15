# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate

from .base import BaseFileSchema
from ..metadata import BoldMetadataSchema


class BidsFileSchema(BaseFileSchema):
    datatype = fields.Str(default="bids", validate=validate.Equal("bids"))
    metadata = fields.Nested(BoldMetadataSchema())
