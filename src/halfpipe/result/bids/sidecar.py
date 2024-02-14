# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from inflection import camelize, underscore

from ...collect.metadata import metadata_fields
from ...logging import logger
from ...utils.json import TypeAwareJSONEncoder
from ...utils.path import AnyPath, split_ext

key_to_bids_map: Mapping[str, str] = dict(
    ica_aroma="ICAAROMA",
    fwhm="FWHM",
    hp_width="HighPassWidth",
    lp_width="LowPassWidth",
    fd_perc="FDPerc",
    fd_mean="FDMean",
    mean_gm_tsnr="MeanGMTSNR",
    mean_seed_tsnr="MeanSeedTSNR",
    mean_component_tsnr="MeanComponentTSNR",
    mean_atlas_tsnr="MeanAtlasTSNR",
    halfpipe_version="HALFpipeVersion",
)

key_from_bids_map: Mapping[str, str] = {v: k for k, v in key_to_bids_map.items()}


def get_sidecar_path(path: AnyPath) -> Path:
    stem, _ = split_ext(path)
    sidecar_path = path.parent / f"{stem}.json"  # type: ignore
    return sidecar_path


def translate_sidecar(value: Any, translate_key: Callable[[str], str]):
    if not isinstance(value, dict):
        return value

    return {translate_key(k): translate_sidecar(v, translate_key) for k, v in value.items()}


def translate_from_bids(key):
    if key in key_from_bids_map:
        return key_from_bids_map[key]
    else:
        return underscore(key)


def translate_to_bids(key):
    if key in key_to_bids_map:
        return key_to_bids_map[key]
    else:
        return camelize(key)


def load_sidecar(path: AnyPath) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar_path = get_sidecar_path(path)
    with sidecar_path.open() as file_handle:
        try:
            sidecar = json.load(file_handle)
        except json.JSONDecodeError:
            logger.warning(f'Could not load sidecar file "{sidecar_path}"', exc_info=True)
            sidecar = dict()

    sidecar = translate_sidecar(sidecar, translate_from_bids)

    metadata: dict[str, Any] = {k: v for k, v in sidecar.items() if k in metadata_fields}

    vals: dict[str, Any] = {k: v for k, v in sidecar.items() if k not in metadata_fields}

    return metadata, vals


def save_sidecar(path: Path, metadata: dict[str, Any], vals: dict[str, Any]):
    sidecar = metadata.copy()
    sidecar.update(vals)

    sidecar = translate_sidecar(sidecar, translate_to_bids)

    sidecar_json = json.dumps(sidecar, cls=TypeAwareJSONEncoder, sort_keys=True, indent=4)

    sidecar_path = get_sidecar_path(path)
    with sidecar_path.open("w") as file_handle:
        file_handle.write(sidecar_json)
