# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Type

from marshmallow import Schema, fields
from marshmallow_oneofschema.one_of_schema import OneOfSchema


def get_nested_schema_field_names(schema, key: str):
    if isinstance(schema, type):
        schema = schema()

    assert isinstance(schema, Schema)

    nested_field = schema.fields[key]

    assert isinstance(nested_field, fields.Nested)

    nested_schema = nested_field.nested

    if isinstance(nested_schema, type):
        nested_schema = nested_schema()

    assert isinstance(nested_schema, Schema)

    field_names = list(nested_schema.fields.keys())

    return field_names


def get_schema_entities(schema):
    return get_nested_schema_field_names(schema, "tags")


def get_type_schema(base_schema: Type[OneOfSchema], database, file_path) -> Type[Schema]:
    # traverse schemas to find subclass
    schema: Type[OneOfSchema] = base_schema
    while hasattr(schema, "type_field") and hasattr(schema, "type_schemas"):
        type_field = schema.type_field
        type_schemas = schema.type_schemas
        v = database.tagval(file_path, type_field)
        schema = type_schemas[v]
    return schema
