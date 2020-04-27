# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import Schema, fields, post_load, validate, post_dump

derivative_entities = [
    "smoothed",
    "band_pass_filtered",
    "confounds_removed",
    "space",
    "desc",
]


class BaseTag:
    def as_tupl(self):
        raise NotImplementedError

    def __hash__(self):
        return hash(self.as_tupl())


class SmoothedTag(BaseTag):
    def __init__(self, **kwargs):
        self.fwhm = kwargs.get("fwhm")

    def as_tupl(self):
        return ("smoothed", self.fwhm)


class BandPassFilteredTag(BaseTag):
    def __init__(self, **kwargs):
        self.type = kwargs.get("type")
        self.low = kwargs.get("low")
        self.high = kwargs.get("high")

    def as_tupl(self):
        if self.type == "gaussian":
            return ("band_pass_filtered", (self.type, self.high))
        elif self.type == "frequency_based":
            return ("band_pass_filtered", (self.type, self.high, self.low))
        else:
            raise ValueError(f'Unknown BandPassFilteredTag type "{self.type}"')


class ConfoundsRemovedTag(BaseTag):
    def __init__(self, **kwargs):
        self.names = kwargs.get("names")

    def as_tupl(self):
        return ("confounds_removed", tuple(sorted(self.names)))


class BaseSchema(Schema):
    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}


class SmoothedTagSchema(BaseSchema):
    fwhm = fields.Float()

    @post_load
    def make_object(self, data, **kwargs):
        return SmoothedTag(**data)


class BandPassFilteredTagSchema(BaseSchema):
    type = fields.Str(validate=validate.OneOf(["gaussian", "frequency_based"]))
    low = fields.Float()
    high = fields.Float()

    @post_load
    def make_object(self, data, **kwargs):
        return BandPassFilteredTag(**data)


class ConfoundsRemovedTagSchema(BaseSchema):
    names = fields.List(fields.Str())

    @post_load
    def make_object(self, data, **kwargs):
        return ConfoundsRemovedTag(**data)
