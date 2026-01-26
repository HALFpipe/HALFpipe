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
    path = str(path)  # ensure string
    metadata: dict[str, Any] = OrderedDict()

    logger.debug(f"Collecting metadata for file: {path}")

    # ---- Add setting if provided ----
    if setting is not None:
        metadata["setting"] = BaseSettingSchema().dump(setting)
        logger.debug(f"Added setting to metadata: {metadata['setting']}")

    # ---- Load schema for the file ----
    schema = get_type_schema(FileSchema, database, path)
    instance = schema()

    # ---- Handle "metadata" field if present ----
    if "metadata" in instance.fields:
        logger.debug(f'"metadata" field detected in schema for {path}')

        # Manual conversion for func datatype
        if database.tagval(path, "datatype") == "func":
            task = database.tagval(path, "task")
            if task is not None:
                metadata["task_name"] = task
                logger.debug(f"Added task_name: {task}")

        # Automated conversion
        metadata_keys = get_nested_schema_field_names(instance, "metadata")
        for key in metadata_keys:
            database.fillmetadata(key, [path])
            value = database.metadata(path, key)

            if value is not None:
                # Transform metadata
                if key.endswith("direction"):
                    try:
                        value = canonicalize_direction_code(value, path)
                        logger.debug(f"Canonicalized {key} -> {value}")
                    except ValueError as e:
                        logger.warning(f'Cannot canonicalize "{key}" for "{path}": {e}', exc_info=False)
                        continue

                if key == "slice_timing_code":
                    if not database.fillmetadata("slice_timing", [path]):
                        logger.debug(f"Slice timing not available for {path}, skipping")
                        continue
                    key = "slice_timing"
                    value = database.metadata(path, key)
                    logger.debug(f"Collected slice_timing: {value}")

                metadata[key] = value
                logger.debug(f"Added metadata key: {key} -> {value}")

    # ---- NIfTI header extraction ----
    header, _ = NiftiheaderLoader.load(path)
    if isinstance(header, Nifti1Header):
        zooms = list(map(float, header.get_zooms()))
        if all(isinstance(z, float) for z in zooms):
            metadata["acquisition_voxel_size"] = tuple(zooms[:3])
            logger.debug(f"Set acquisition_voxel_size: {metadata['acquisition_voxel_size']}")

        data_shape = header.get_data_shape()
        metadata["acquisition_volume_shape"] = tuple(data_shape[:3])
        logger.debug(f"Set acquisition_volume_shape: {metadata['acquisition_volume_shape']}")

        if len(data_shape) == 4:
            metadata["number_of_volumes"] = int(data_shape[3])
            logger.debug(f"Set number_of_volumes: {metadata['number_of_volumes']}")

    # ---- Orientation codes ----
    axcodes_set = get_axcodes_set(path)
    if len(axcodes_set) == 1:
        (axcodes,) = axcodes_set
        axcode_str = "".join(axcodes)
        metadata["acquisition_orientation"] = axcode_str
        logger.debug(f"Set acquisition_orientation: {axcode_str}")

    # ---- Validate metadata keys ----
    unknown_keys = set(metadata.keys()) - metadata_fields
    if unknown_keys:
        unknown_keys_str = inflect_engine.join([f'"{key}"' for key in sorted(unknown_keys)])
        raise ValueError(f"Collected unknown metadata keys {unknown_keys_str}")

    logger.info(f"Collected metadata for {path}: {metadata.keys()}")
    return metadata
