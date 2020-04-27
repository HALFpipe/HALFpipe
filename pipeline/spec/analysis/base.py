# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, Schema, post_load, post_dump, validates_schema, ValidationError


analysisattrnames = [
    "name",
    "level",
    "input",
    "filter",
    "across",
    "type",
    "tags",
    "variables",
    "contrasts",
    "spreadsheet",
]


class Analysis:
    attrnames = analysisattrnames

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
        return hash(self.name)  # name is unique


class BaseAnalysisSchema(Schema):
    name = fields.Str()

    @post_load
    def make_object(self, data, **kwargs):
        return Analysis(**data)

    @validates_schema
    def validate_variables(self, data, **kwargs):
        if "variables" in data:
            seen_names = set()
            for variable in data["variables"]:
                if variable.name in seen_names:
                    raise ValidationError("variable name must be unique")

    @post_dump(pass_many=False)
    def remove_none(self, data, many):
        return {key: value for key, value in data.items() if value is not None}
