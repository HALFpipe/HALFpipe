# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate

from ..metadata import BoldMetadataSchema
from .base import BaseFileSchema


class BidsFileSchema(BaseFileSchema):
    datatype = fields.Str(dump_default="bids", validate=validate.Equal("bids"))
    metadata = fields.Nested(BoldMetadataSchema())
