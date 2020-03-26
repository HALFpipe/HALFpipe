# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, Schema, post_load, post_dump


class Analysis:
    def __init__(self, **kwargs):
        self.level = kwargs.get("level")
        self.input = kwargs.get("input")
        self.filter = kwargs.get("filter")
        self.across = kwargs.get("across")
        self.name = kwargs.get("name")
        self.type = kwargs.get("type")
        self.tags = kwargs.get("tags")
        self.variables = kwargs.get("variables")
        self.contrasts = kwargs.get("contrasts")
        self.spreadsheet = kwargs.get("spreadsheet")


class BaseAnalysisSchema(Schema):
    name = fields.Str()

    @post_load
    def make_object(self, data, **kwargs):
        return Analysis(**data)

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}
