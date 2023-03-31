# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .anat import schemas as AnatTagsSchemas
from .base import schemas as BaseTagsSchemas
from .fmap import schemas as FmapTagsSchemas
from .func import schemas as FuncTagsSchemas
from .ref import schemas as RefTagsSchemas
from .resultdict import ResultdictTagsSchema, resultdict_entities

schemas = [
    *BaseTagsSchemas,
    *AnatTagsSchemas,
    *FuncTagsSchemas,
    *FmapTagsSchemas,
    *RefTagsSchemas,
    ResultdictTagsSchema,
]

entities_list = ["run", "task", "ses", "sub"]
for schema in schemas:  # automatically add other entities
    instance = schema()
    for key in instance.fields.keys():
        if key not in entities_list:
            entities_list.insert(0, key)
for entity in resultdict_entities:
    entities_list.remove(entity)
    entities_list.insert(0, entity)  # maintain order for outputs

entities = tuple(entities_list)

entity_longnames = {
    "ses": "session",
    "sub": "subject",
    "dir": "direction",
    "acq": "acquisition",
}
