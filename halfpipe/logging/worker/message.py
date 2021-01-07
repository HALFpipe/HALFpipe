# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

import logging

from marshmallow import Schema, fields, validate, post_load
from marshmallow_oneofschema import OneOfSchema


class Message:
    def __init__(self, type: str, **kwargs):
        self.type = type
        self.levelno: Optional[int] = None
        self.msg: Optional[str] = None
        self.workdir = None
        for k, v in kwargs.items():
            setattr(self, k, v)


class BaseMessageSchema(Schema):
    type = fields.Str(validate=validate.OneOf([
        "enable_verbose",
        "enable_print",
        "disable_print",
        "teardown",
    ]))

    @post_load
    def make_object(self, data, **kwargs):
        return Message(**data)


class LogMessageSchema(BaseMessageSchema):
    type = fields.Str(default="log", validate=validate.Equal("log"))

    levelno = fields.Int(default=logging.DEBUG)

    msg = fields.Str(required=True)


class SetWorkdirMessageSchema(BaseMessageSchema):
    type = fields.Str(default="set_workdir", validate=validate.Equal("set_workdir"))

    workdir = fields.Str(required=True)


class MessageSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "log": LogMessageSchema,
        "set_workdir": SetWorkdirMessageSchema,
        "enable_verbose": BaseMessageSchema,
        "enable_print": BaseMessageSchema,
        "disable_print": BaseMessageSchema,
        "teardown": BaseMessageSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, Message):
            return obj.type
        elif isinstance(obj, dict):
            return obj.get("type")
