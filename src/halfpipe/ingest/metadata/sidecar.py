# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from functools import lru_cache
from pathlib import Path

import marshmallow.exceptions
from inflection import underscore
from marshmallow import EXCLUDE

from ...model.file.base import File
from ...model.metadata import MetadataSchema
from ...utils.path import split_ext
from .base import Loader


class SidecarMetadataLoader(Loader):
    @staticmethod
    @lru_cache(maxsize=None)
    def load_json(file_path) -> dict:
        stem, _ = split_ext(file_path)
        sidecar_file_path = Path(file_path).parent / f"{stem}.json"

        if not Path(sidecar_file_path).is_file():
            return dict()

        with open(sidecar_file_path, "r") as sidecar_file_handle:
            sidecar_file_contents = sidecar_file_handle.read()

        return json.loads(sidecar_file_contents)

    @classmethod
    @lru_cache(maxsize=None)
    def load(cls, file_path) -> dict:
        try:
            in_data = cls.load_json(file_path)

            in_data = {underscore(k): v for k, v in in_data.items()}
            sidecar = MetadataSchema().load(in_data, unknown=EXCLUDE)

        except marshmallow.exceptions.ValidationError:
            return dict()

        return sidecar

    def fill(self, fileobj: File, key: str) -> bool:
        sidecar = self.load(fileobj.path)

        value = sidecar.get(key)

        if value is None:
            return False

        fileobj.metadata[key] = value

        return True
