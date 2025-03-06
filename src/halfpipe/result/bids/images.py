# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Mapping

from tqdm.auto import tqdm

from ...file_index.base import FileIndex
from ...logging import logger
from ...model.tags.schema import entities
from ...stats.algorithms import algorithms
from ...utils.multiprocessing import make_pool_or_null_context
from ...utils.path import copy_if_newer, split_ext
from ..base import ResultDict
from .base import make_bids_path
from .sidecar import load_sidecar, save_sidecar

boldmap_keys: frozenset[str] = frozenset(["tsnr"])
statmap_keys: frozenset[str] = frozenset(["effect", "variance", "z", "t", "f", "dof", "sigmasquareds"])
has_sidecar_keys: frozenset[str] = frozenset(["effect", "reho", "falff", "alff", "bold", "timeseries"])
has_sidecar_extensions: frozenset[str] = frozenset([".nii", ".nii.gz", ".tsv"])


def _from_bids_derivatives(tags: Mapping[str, str | None]) -> str | None:
    suffix = tags["suffix"]
    if suffix in ["boldmap", "statmap"]:
        if "stat" not in tags:
            return None

        stat = tags["stat"]

        if "algorithm" in tags:
            algorithm = tags["algorithm"]
            if algorithm in ["mcar"]:
                return f"{algorithm}{stat}"

        return stat

    return suffix


def _to_bids_derivatives(key: str, inpath: Path, tags: dict[str, str]) -> Path:
    if key in statmap_keys:  # apply rule
        return make_bids_path(inpath, "image", tags, suffix="statmap", stat=key)
    elif key in boldmap_keys:  # apply rule
        return make_bids_path(inpath, "image", tags, suffix="boldmap", stat=key)

    elif key in algorithms["heterogeneity"].model_outputs:
        key = re.sub(r"^het", "", key)
        return make_bids_path(
            inpath,
            "image",
            tags,
            "statmap",
            algorithm="heterogeneity",
            stat=key,
        )
    elif key in algorithms["mcartest"].model_outputs:
        key = re.sub(r"^mcar", "", key)
        return make_bids_path(inpath, "image", tags, suffix="statmap", algorithm="mcar", stat=key)

    else:
        return make_bids_path(inpath, "image", tags, suffix=key)


def _load_result(file_index: FileIndex, tags: Mapping[str, str | None]) -> ResultDict | None:
    paths = file_index.get(**tags)
    if paths is None or len(paths) == 0:
        return None

    result: ResultDict = defaultdict(dict)
    result["tags"] = {key: value for key, value in tags.items() if value is not None}

    for path in paths:
        if path.suffix == ".json":
            metadata, vals = load_sidecar(path)
            result["metadata"].update(metadata)
            result["vals"].update(vals)
            continue
        elif path.suffix in {".html"}:
            continue

        if isinstance(path, Path):
            if path.stat(follow_symlinks=True).st_size == 0:
                logger.warning(f'Skipping empty file "{path}"')
                continue

        key = _from_bids_derivatives(file_index.get_tags(path))
        if key is None:
            continue

        result["images"][key] = path

    if not has_sidecar_keys.isdisjoint(result["images"].keys()):
        if len(result["metadata"]) == 0 and len(result["vals"]) == 0:
            image_files = [str(image_file) for image_file in result["images"].values()]
            extensions = {split_ext(image_file)[-1] for image_file in image_files}
            if not extensions.isdisjoint(has_sidecar_extensions):
                logger.warning(
                    f"Could not find metadata for files {image_files}. Check if the `.json` sidecar files are present."
                )

    return dict(result)


def load_images(file_index: FileIndex, num_threads: int = 1) -> list[ResultDict]:
    image_group_entities = set(entities) - {"stat", "algorithm"}

    groups = file_index.get_tag_groups(image_group_entities)

    cm, iterator = make_pool_or_null_context(
        groups,
        callable=partial(_load_result, file_index),
        num_threads=num_threads,
        chunksize=None,
    )

    results = list()
    with cm:
        for result in tqdm(
            iterator,
            desc="loading image metadata",
            total=len(groups),
        ):
            if result is None:
                continue
            results.append(result)

    return results


def save_images(results: list[ResultDict], base_directory: Path, remove: bool = False):
    derivatives_directory = base_directory / "derivatives" / "halfpipe"
    grouplevel_directory = base_directory / "grouplevel"

    for result in results:
        tags = result.get("tags", dict())
        metadata = result.get("metadata", dict())
        vals = result.get("vals", dict())
        images = result.get("images", dict())

        # images

        for key, inpath in images.items():
            outpath = derivatives_directory

            if "sub" not in tags:
                outpath = grouplevel_directory

            outpath = outpath / _to_bids_derivatives(key, inpath, tags)

            was_updated = copy_if_newer(inpath, outpath)

            if remove:
                inpath.unlink()

            if was_updated:
                # TODO make plot
                pass

            _, extension = split_ext(outpath)
            if key in has_sidecar_keys:
                if extension in has_sidecar_extensions:
                    save_sidecar(outpath, metadata, vals)
