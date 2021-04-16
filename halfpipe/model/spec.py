# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import Optional
import logging
import os
from os import path as op
from datetime import datetime as dt
import uuid

from marshmallow import (
    fields,
    Schema,
    post_load,
    RAISE,
    validate,
    validates_schema,
    ValidationError,
)
import marshmallow.exceptions
from inflection import humanize

from .. import __version__ as halfpipe_version
from .file import File, FileSchema
from .setting import SettingSchema, GlobalSettingsSchema
from .feature import FeatureSchema
from .model import ModelSchema
from ..utils import hexdigest

entity_aliases = {"direction": "phase_encoding_direction"}
timestampfmt = "%Y-%m-%d_%H-%M"
namespace = uuid.UUID("be028ae6-9a73-11ea-8002-000000000000")  # constant

schema_version = "3.0"
compatible_schema_versions = ["3.0"]


class SpecSchema(Schema):
    class Meta:
        unknown = RAISE
        ordered = True

    halfpipe_version = fields.Str(default=halfpipe_version)
    schema_version = fields.Str(
        default=schema_version, validate=validate.OneOf(compatible_schema_versions), required=True
    )
    timestamp = fields.DateTime(default=dt.now(), format=timestampfmt, required=True)

    global_settings = fields.Nested(GlobalSettingsSchema, default={})

    files = fields.List(fields.Nested(FileSchema), default=[], required=True)
    settings = fields.List(fields.Nested(SettingSchema), default=[], required=True)
    features = fields.List(fields.Nested(FeatureSchema), default=[], required=True)
    models = fields.List(fields.Nested(ModelSchema), default=[], required=True)

    @validates_schema
    def validate_analyses(self, data, **kwargs):
        names = []
        for field in ["settings", "features", "models"]:
            if field not in data:
                continue  # validation error will be raised independently
            names.extend([a["name"] if isinstance(a, dict) else a.name for a in data[field]])
        if len(names) > len(set(names)):
            raise ValidationError("Duplicate name")

    @validates_schema
    def validate_files(self, data, **kwargs):
        if "files" not in data:
            return  # validation error will be raised independently
        descSets = {"seed": set(), "map": set()}
        if not isinstance(data["files"], list):
            return  # validation error will be raised independently
        for fileobj in data["files"]:

            if not isinstance(fileobj, File):
                raise ValidationError("List elements need to be File objects")

            if hasattr(fileobj, "tags"):
                desc = fileobj.tags.get("desc")
                if fileobj.suffix in descSets:
                    descSet = descSets[fileobj.suffix]
                    if desc in descSet:
                        raise ValidationError(f"{humanize(fileobj.suffix)} names need to be unique")

                    descSet.add(desc)

    @validates_schema
    def validate_models(self, data, **kwargs):
        if "models" not in data or "files" not in data:
            return  # validation error will be raised independently

        spreadsheets = set(file.path for file in data["files"] if file.datatype == "spreadsheet")

        for model in data["models"]:

            if model.type == "lme":
                if model.spreadsheet not in spreadsheets:
                    raise ValidationError(f'Spreadsheet "{model.spreadsheet}" not found in files')

    @post_load
    def make_object(self, data, **kwargs):
        return Spec(**data)


class Spec:
    def __init__(self, timestamp, files, **kwargs):
        self.timestamp = timestamp
        self.files = files

        self.global_settings = dict()

        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def timestampstr(self):
        return self.timestamp.strftime(timestampfmt)

    @property
    def uuid(self):
        return uuid.uuid5(namespace, hexdigest(SpecSchema().dump(self)))

    def validate(self):
        SpecSchema().validate(self.__dict__)

    def put(self, fileobj):
        for file in self.files:
            if file.path == fileobj.path:  # path must be unique
                return
        self.files.append(fileobj)


def loadspec(workdir=None, timestamp=None, specpath=None, logger=logging.getLogger("halfpipe")) -> Optional[Spec]:
    if specpath is None:
        assert workdir is not None
        if timestamp is not None:
            timestampstr = timestamp.strftime(timestampfmt)
            specpath = op.join(workdir, f"spec.{timestampstr}.json")
        else:
            specpath = op.join(workdir, "spec.json")
    if not op.isfile(specpath):
        return

    logger.info(f"Loading spec file {specpath}")
    with open(specpath, "r") as f:
        jsn = f.read()

    try:
        spec = SpecSchema().loads(jsn, many=False)
        assert isinstance(spec, Spec)
        return spec
    except marshmallow.exceptions.ValidationError as e:
        logger.warning(f'Ignored validation error in "{specpath}"', exc_info=e)


def savespec(spec: Spec, workdir=None, specpath=None, logger=logging.getLogger("halfpipe")):
    os.makedirs(workdir, exist_ok=True)
    if specpath is None:
        assert workdir is not None
        specpath = op.join(workdir, "spec.json")
    if op.isfile(specpath):
        spectomove = loadspec(specpath=specpath)
        if spectomove is None:
            logger.warning("Overwriting invalid spec file")
        else:
            newspecpath = op.join(workdir, f"spec.{spectomove.timestampstr}.json")
            logger.info(f'Moving previous spec file from "{specpath}" to "{newspecpath}"')
            if op.isfile(newspecpath):
                logger.warning("Found specpath timestampstr collision, overwriting")
            os.replace(specpath, newspecpath)
    jsn = SpecSchema().dumps(spec, many=False, indent=4, sort_keys=False)
    with open(specpath, "w") as f:
        f.write(jsn)
