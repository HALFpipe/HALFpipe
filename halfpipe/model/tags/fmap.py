# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .base import AcqTagsSchema
from .func import FuncTagsSchema


class FmapTagsSchema(FuncTagsSchema, AcqTagsSchema):
    pass


class EPIFmapTagsSchema(FmapTagsSchema):
    pass


schemas = [FmapTagsSchema, EPIFmapTagsSchema]
