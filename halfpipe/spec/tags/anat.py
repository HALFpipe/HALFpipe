# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, validate

from .base import BaseSchema


class AnatTagsSchema(BaseSchema):
    datatype = fields.Constant("anat")

    suffix = fields.Str(validate=validate.OneOf(["T1w"]))
    extension = fields.Str(validate=validate.OneOf(["nii", "nii.gz"]))

    subject = fields.Str()
