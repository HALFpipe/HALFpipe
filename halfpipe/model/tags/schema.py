# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .anat import __all__ as AnatTagsSchemas
from .base import __all__ as BaseTagsSchemas
from .fmap import __all__ as FmapTagsSchemas
from .func import __all__ as FuncTagsSchemas
from .ref import __all__ as RefTagsSchemas
from .resultdict import ResultdictTagsSchema, resultdict_entities

__all__ = [
    *BaseTagsSchemas,
    *AnatTagsSchemas,
    *FuncTagsSchemas,
    *FmapTagsSchemas,
    *RefTagsSchemas,
    ResultdictTagsSchema,
]

entities = ["run", "task", "ses", "sub"]
for schema in __all__:  # automatically add other entities
    instance = schema()
    for key in instance.fields.keys():
        if key not in entities:
            entities.insert(0, key)
for entity in resultdict_entities:
    entities.remove(entity)
    entities.insert(0, entity)  # maintain order for outputs
entities = tuple(entities)

entity_longnames = {
    "ses": "session",
    "sub": "subject",
    "dir": "direction",
    "acq": "acquisition",
}
