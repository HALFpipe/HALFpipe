# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from ..utils.path import split_ext
from .base import FileIndex


def parse(path: Path) -> dict[str, str] | None:
    if path.is_dir():
        return None  # skip directories

    stem, extension = split_ext(path)
    if stem.startswith("."):
        return None  # skip hidden files

    tokens = stem.split("_")

    # parse tokens
    keys = list()
    values = list()
    for token in tokens:
        if "-" in token:  # a bids tag
            key = token.split("-")[0]

            keys.append(key)
            values.append(token[len(key) + 1 :])

        else:  # a suffix
            keys.append(None)
            values.append(token)

    # extract bids suffixes
    suffixes: list[str] = list()
    while keys and keys[-1] is None:
        keys.pop(-1)
        suffixes.insert(0, values.pop(-1))

    # merge other suffixes with their preceding tag value
    for i, (key, value) in enumerate(zip(keys, values)):
        if key is not None:
            continue
        if i < 1:
            continue
        values[i - 1] += f"_{value}"

    # build tags
    tags = dict(
        suffix="_".join(suffixes),
    )

    if extension:
        tags["extension"] = extension

    for key, value in zip(keys, values):
        if key is not None:
            tags[key] = value

    return tags


class BIDSIndex(FileIndex):
    def put(self, root: Path):
        for path in root.glob("**/*"):
            tags = parse(path)

            if tags is None:
                continue  # not a valid path

            for key, value in tags.items():
                self.paths_by_tags[key][value].add(path)

            self.tags_by_paths[path] = tags
