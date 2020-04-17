# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, Schema, post_load, post_dump


class Analysis:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.level = kwargs.get("level")
        self.input = kwargs.get("input")
        self.filter = kwargs.get("filter")
        self.across = kwargs.get("across")
        self.type = kwargs.get("type")
        self.tags = kwargs.get("tags")
        self.variables = kwargs.get("variables")
        self.contrasts = kwargs.get("contrasts")
        self.spreadsheet = kwargs.get("spreadsheet")

    def __hash__(self):
        safeinput = None
        if self.input is not None:
            safeinput = tuple(self.input)
        safefilter = None
        if self.filter is not None:
            safefilter = tuple(self.filter)
        safevariables = None
        if self.variables is not None:
            safevariables = tuple(self.variables)
        safecontrasts = None
        if self.contrasts is not None:
            safecontrasts = tuple(self.contrasts)
        return hash(
            (
                "analysis",
                self.name,
                self.level,
                safeinput,
                safefilter,
                self.across,
                self.type,
                self.tags,
                safevariables,
                safecontrasts,
                self.spreadsheet,
            )
        )


class BaseAnalysisSchema(Schema):
    name = fields.Str()

    @post_load
    def make_object(self, data, **kwargs):
        return Analysis(**data)

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}
