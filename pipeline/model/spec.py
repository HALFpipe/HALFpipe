# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import marshmallow
import marshmallow.fields
from marshmallow_oneofschema import OneOfSchema


class Spec:
    def __init__(self, files, tags, analyses, settings):
        self.files = files
        self.analyses = analyses
        self.settings = settings


class FileSpec:
    def __init__(self, pattern, tags):
        self.pattern = pattern
        self.tags = tags


class TagSpec:
    def __init__(self, entity, value):
        self.entity = entity
        self.value = value





class ContrastSpec:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class SpecSchema():



class AnalysisListSchema(OneOfSchema):
    type_field = "level"
    type_schemas = {"Foo": FooSchema, "Bar": BarSchema}
    
class SubjectLevelAnalysisSchema():
    
