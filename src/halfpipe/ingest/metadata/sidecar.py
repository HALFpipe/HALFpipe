# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import marshmallow.exceptions
from inflection import underscore
from marshmallow import EXCLUDE
from sdcflows.utils.epimanip import get_trt

from ...model.file.base import File
from ...model.metadata import MetadataSchema
from ...utils.path import split_ext
from .base import Loader

if TYPE_CHECKING:
    from ..resolve import ResolvedSpec


@cache
def _load_json(path: Path) -> dict:
    if not path.is_file():
        return dict()

    with path.open("r") as sidecar_file_handle:
        sidecar_file_contents = sidecar_file_handle.read()

    return json.loads(sidecar_file_contents)


def _load_sidecar(resolved_spec: "ResolvedSpec | None", path: Path) -> dict[str, Any]:
    sidecar_paths: list[Path] | None = None
    if resolved_spec is not None:
        sidecar_paths = resolved_spec.sidecar_paths_by_filepaths.get(str(path))
    if sidecar_paths is None:
        stem, _ = split_ext(path)
        sidecar_paths = [Path(path).parent / f"{stem}.json"]
    in_data: dict[str, Any] = dict()
    for sidecar_path in sidecar_paths:
        sidecar_data = _load_json(sidecar_path)
        in_data.update(sidecar_data)
    return in_data


class SidecarMetadataLoader(Loader):
    def __init__(self, resolved_spec: "ResolvedSpec | None" = None) -> None:
        self.resolved_spec = resolved_spec

    def load(self, file_path: str | Path) -> dict:
        in_data = {underscore(key): value for key, value in _load_sidecar(self.resolved_spec, Path(file_path)).items()}

        # Normalize intended_for, b0_field_identifier, and b0_field_source to lists of
        # strings, since the schema expects lists of strings
        for key in ("intended_for", "b0_field_identifier", "b0_field_source"):
            value = in_data.get(key)
            if isinstance(value, str):
                in_data[key] = [value]

        try:
            sidecar = MetadataSchema().load(in_data, unknown=EXCLUDE)
        except marshmallow.exceptions.ValidationError:
            return dict()

        return sidecar

    def fill(self, fileobj: File, key: str) -> bool:
        sidecar = self.load(fileobj.path)
        value = sidecar.get(key)

        if key == "total_readout_time" and value is None:
            sidecar = _load_sidecar(self.resolved_spec, Path(fileobj.path))
            try:
                value = get_trt(sidecar, in_file=fileobj.path)
            except Exception:
                pass

        if value is None:
            return False

        fileobj.metadata[key] = value

        return True
