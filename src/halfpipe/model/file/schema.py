# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """

from marshmallow_oneofschema import OneOfSchema

from .anat import AnatFileSchema
from .base import File
from .bids import BidsFileSchema
from .fmap import FmapFileSchema
from .func import FuncFileSchema
from .ref import RefFileSchema
from .spreadsheet import SpreadsheetFileSchema


class FileSchema(OneOfSchema):
    type_field = "datatype"
    type_field_remove = False
    type_schemas = {
        "bids": BidsFileSchema,
        "anat": AnatFileSchema,
        "fmap": FmapFileSchema,
        "func": FuncFileSchema,
        "ref": RefFileSchema,
        "spreadsheet": SpreadsheetFileSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, File):
            return obj.datatype
        raise Exception("Cannot get obj type for FileSchema")
