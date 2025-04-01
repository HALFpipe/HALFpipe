# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .anat import schemas as anat_tags_schemas
from .base import schemas as base_tags_schemas
from .fmap import schemas as fmap_tags_schemas
from .func import schemas as func_tags_schemas
from .ref import schemas as ref_tags_schemas
from .resultdict import ResultdictTagsSchema, resultdict_entities

schemas = [
    *base_tags_schemas,
    *anat_tags_schemas,
    *func_tags_schemas,
    *fmap_tags_schemas,
    *ref_tags_schemas,
    ResultdictTagsSchema,
]

entities_list = ["run", "ses", "task", "sub"]
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
