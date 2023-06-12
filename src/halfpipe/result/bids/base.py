# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Literal

from ...model.tags import entities
from ...model.tags.resultdict import first_level_entities
from ...utils.format import format_like_bids
from ...utils.path import split_ext


def join_tags(tags: dict[str, str], entities: list[str] | None = None) -> str | None:
    joined = None

    if entities is None:
        entities = list(tags.keys())

    for entity in entities:
        if entity not in tags:
            continue
        value = tags[entity]
        value = format_like_bids(value)

        if joined is None:
            joined = f"{entity}-{value}"
        else:
            joined = f"{joined}_{entity}-{value}"

    return joined


def make_bids_prefix(tags: dict[str, str]) -> str | None:
    prefix = join_tags(tags, list(reversed(entities)))
    return prefix


def make_bids_path(
    source_file: Path | str,
    source_type: Literal["image", "report"],
    tags: dict[str, str],
    suffix: str,
    **kwargs: str,
) -> Path:
    path = Path()

    for entity in ["sub", "ses"]:
        folder_name = join_tags(tags, [entity])
        if folder_name is not None:
            path = path.joinpath(folder_name)

    path = path.joinpath(dict(image="func", report="figures")[source_type])

    if "feature" in tags:  # make subfolders for all feature outputs
        folder_entities = ["task"]
        if "sub" not in tags:
            folder_entities.extend(first_level_entities)

        folder_name = join_tags(tags, folder_entities)
        if folder_name is not None:
            path = path.joinpath(folder_name)

    if "model" in tags:
        folder_name = join_tags(tags, ["model"])
        assert folder_name is not None
        path = path.joinpath(folder_name)

    _, ext = split_ext(source_file)
    filename = f"{suffix}{ext}"  # keep original extension

    kwargs_str = join_tags(kwargs)
    if kwargs_str is not None:
        filename = f"{kwargs_str}_{filename}"

    tags_str = make_bids_prefix(tags)
    if tags_str is not None:
        filename = f"{tags_str}_{filename}"

    return path / filename
