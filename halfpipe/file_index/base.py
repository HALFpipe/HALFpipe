# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
from pathlib import Path
from typing import Container, Mapping

from pyrsistent import pmap

from ..utils import logger


class FileIndex:
    def __init__(self) -> None:
        self.paths_by_tags: dict[str, dict[str, set[Path]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self.tags_by_paths: dict[Path, dict[str, str]] = defaultdict(dict)

    @property
    def hexdigest(self) -> str:
        """
        A fourty character hash code of the paths in the index, obtained using the `sha1` algorithm.
        """
        hash_algorithm = sha1()

        for path in sorted(self.tags_by_paths.keys()):
            path_bytes = str(path).encode()
            hash_algorithm.update(path_bytes)

        return hash_algorithm.hexdigest()

    def get(self, **tags) -> set[Path] | None:
        """
        Find all paths that match the query tags
        """

        res = None

        for key, value in tags.items():
            if key not in self.paths_by_tags:
                logger.info(f'Unknown key "{key}"')
                return None

            values = self.paths_by_tags[key]
            if value not in values:
                logger.info(f'Unknown value "{value}"')
                return None

            paths = values[value]
            if res is not None:
                res &= paths
            else:
                res = paths.copy()

        return res

    def get_tags(self, path: Path) -> Mapping[str, str]:
        return self.tags_by_paths[path]

    def get_tag_value(self, path: Path, key: str) -> str | None:
        return self.get_tags(path).get(key)

    def get_tag_mapping(self, key: str) -> Mapping[str, set[Path]]:
        return self.paths_by_tags[key]

    def get_tag_values(self, key: str, paths: set[Path] | None = None) -> set[str]:
        if key not in self.paths_by_tags:
            return set()

        if paths is None:
            return set(self.paths_by_tags[key].keys())

        return set(
            k for k, v in self.paths_by_tags[key].items() if not paths.isdisjoint(v)
        )

    def get_tag_groups(
        self, keys: Container[str], paths: set[Path] | None = None
    ) -> list[Mapping[str, str]]:
        if paths is None:
            paths = set(self.tags_by_paths.keys())

        groups: set[Mapping[str, str]] = {
            pmap({k: v for k, v in self.tags_by_paths[path].items() if k in keys})
            for path in paths
        }

        return [dict(group) for group in groups]

    def recode(self, key: str, value: str, replacement: str):
        """
        Replace the value `value` with `replacement` for the tag `key`
        """
        values = self.paths_by_tags[key]
        if value in values:
            values[replacement].update(values.pop(value))

        for tags in self.tags_by_paths.values():
            if key in tags:
                if tags[key] == value:
                    tags[key] = replacement

    def update(self, other: FileIndex):
        raise NotImplementedError  # TODO
