# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .anat import AnatTagsSchema
from .func import FuncTagsSchema, BoldTagsSchema, TxtEventsTagsSchema
from .fmap import FmapTagsSchema
from .ref import RefTagsSchema
from .resultdict import ResultdictTagsSchema

from .schema import entities, entity_longnames

__all__ = [
    AnatTagsSchema,
    FuncTagsSchema,
    BoldTagsSchema,
    TxtEventsTagsSchema,
    FmapTagsSchema,
    RefTagsSchema,
    ResultdictTagsSchema,
    entities,
    entity_longnames,
]
