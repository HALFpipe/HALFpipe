# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from enum import Enum, auto

import marshmallow
import marshmallow.fields
from marshmallow_oneofschema import OneOfSchema
from marshmallow_enum import EnumField


class ExtensionTag(Enum):
    nii = "nii"
    nii_gz = "nii.gz"
    json = "json"
    tsv = "tsv"


class DatatypeTag(Enum):
    func = auto()
    anat = auto()
    fmap = auto()




class PhaseEncodingDirectionTag:
    def __init__(self, value):
        self.value = value


class SubjectTag:
    def __init__(self, value):
        self.value = value


class RunTag:
    def __init__(self, value):
        self.value = value


class SessionTag:
    def __init__(self, value):
        self.value = value


class TaskTag:
    def __init__(self, value):
        self.value = value


class ConditionTag:
    def __init__(self, value):
        self.value = value


class AtlasTag:
    def __init__(self, value):
        self.value = value


class SuffixSchema(OneOfSchema):
    type_field = "datatype"
    type_schemas = {"Foo": FooSchema, "Bar": BarSchema}

