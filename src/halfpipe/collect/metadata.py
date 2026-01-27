# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict
from pathlib import Path
from typing import Any

from nibabel.nifti1 import Nifti1Header

from ..ingest.database import Database
from ..ingest.metadata.direction import canonicalize_direction_code, get_axcodes_set
from ..ingest.metadata.niftiheader import NiftiheaderLoader
from ..logging import logger
from ..model.file.schema import FileSchema
from ..model.metadata import MetadataSchema
from ..model.setting import BaseSettingSchema
from ..model.utils import get_nested_schema_field_names, get_type_schema
from ..utils.format import inflect_engine

metadata_fields: frozenset[str] = frozenset(
    [
        *MetadataSchema().fields.keys(),
        "acquisition_voxel_size",
        "acquisition_volume_shape",
        "number_of_volumes",
        "acquisition_orientation",
        "setting",
        "task_name",
    ]
)


def collect_metadata(database: Database, path: Path | str, setting=None) -> dict[str, Any]:
    metadata: dict[str, Any] = OrderedDict()

    if setting is not None:
        metadata["setting"] = BaseSettingSchema().dump(setting)

    schema = get_type_schema(FileSchema, database, path)
    instance = schema()

    if "metadata" in instance.fields:
        # manual conversion
        if database.tagval(path, "datatype") == "func":
            task = database.tagval(path, "task")
            if task is not None:
                metadata["task_name"] = task

        # automated conversion
        metadata_keys = get_nested_schema_field_names(instance, "metadata")
        for key in metadata_keys:
            database.fillmetadata(key, [str(path)])
            value = database.metadata(path, key)

            if value is not None:
                # transform metadata
                if key.endswith("direction"):
                    try:
                        value = canonicalize_direction_code(value, str(path))
                    except ValueError as e:
                        logger.warning(f'Cannot find "{key}" for "{path}"', exc_info=e)
                        continue
                if key == "slice_timing_code":
                    if not database.fillmetadata("slice_timing", [str(path)]):
                        continue
                    key = "slice_timing"
                    value = database.metadata(path, key)
                # write
                metadata[key] = value

    header, _ = NiftiheaderLoader.load(str(path))
    if isinstance(header, Nifti1Header):
        zooms = list(map(float, header.get_zooms()))
        if all(isinstance(z, float) for z in zooms):
            metadata["acquisition_voxel_size"] = tuple(zooms[:3])

        data_shape = header.get_data_shape()
        metadata["acquisition_volume_shape"] = tuple(data_shape[:3])

        if len(data_shape) == 4:
            metadata["number_of_volumes"] = int(data_shape[3])

    axcodes_set = get_axcodes_set(str(path))
    if len(axcodes_set) == 1:
        (axcodes,) = axcodes_set
        axcode_str = "".join(axcodes)
        metadata["acquisition_orientation"] = axcode_str

    if not set(metadata.keys()).issubset(metadata_fields):
        unknown_keys = set(metadata.keys()) - metadata_fields
        unknown_keys_str = inflect_engine.join([f'"{key}"' for key in sorted(unknown_keys)])
        raise ValueError(f"Collected unknown metadata keys {unknown_keys_str}")

    return metadata
