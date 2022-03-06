# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .anat import AnatTagsSchema
from .fmap import EPIFmapTagsSchema, FmapTagsSchema
from .func import BoldTagsSchema, FuncTagsSchema, TxtEventsTagsSchema
from .ref import RefTagsSchema
from .resultdict import ResultdictTagsSchema, resultdict_entities
from .schema import entities, entity_longnames

__all__ = [
    "AnatTagsSchema",
    "FuncTagsSchema",
    "BoldTagsSchema",
    "TxtEventsTagsSchema",
    "FmapTagsSchema",
    "EPIFmapTagsSchema",
    "RefTagsSchema",
    "ResultdictTagsSchema",
    "resultdict_entities",
    "entities",
    "entity_longnames",
]
