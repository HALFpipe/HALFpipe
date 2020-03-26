# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from marshmallow import fields, Schema, post_load

from .file import FileSchema
from .analysis import AnalysisSchema

scan_entities = ["task", "session", "run", "direction", "subject"]
entity_aliases = {"direction": "phase_encoding_direction"}


class Spec:
    def __init__(self, files=[], analyses=[]):
        self.files = files
        self.analyses = analyses

    def _has_datatype(self, datatype):
        res = False
        for file_obj in self.files:
            if file_obj.tags.datatype == datatype:
                res = True
        return res

    def has_anat(self):
        return self._has_datatype("anat")


class SpecSchema(Schema):
    files = fields.List(fields.Nested(FileSchema))
    analyses = fields.List(fields.Nested(AnalysisSchema))

    @post_load
    def make_object(self, data, **kwargs):
        return Spec(**data)
