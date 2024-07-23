# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import zipfile
from collections import defaultdict
from enum import Enum, IntEnum, auto
from glob import glob, has_magic
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from more_itertools import powerset
from pyrsistent import PMap, pmap

from .logging import logger
from .utils.format import format_tags, normalize_subject
from .utils.path import AnyPath


class Rating(IntEnum):
    NONE = -1
    GOOD = 0
    UNCERTAIN = 1
    BAD = 2


class Decision(Enum):
    INCLUDE = auto()
    EXCLUDE = auto()


class QCDecisionMaker:
    def __init__(self, file_paths: Sequence[AnyPath]):
        self.index: dict[PMap[str, str], set[Rating]] = defaultdict(set)
        self.types: set[str] = set()
        self.relevant_tag_names: set[str] = set()

        self.shown_warning_tags: set[Mapping[str, str]] = set()

        for file_path in file_paths:
            self.add_file(file_path)

    def add_file(self, file_path: AnyPath) -> None:
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if has_magic(str(file_path)) and not isinstance(file_path, zipfile.Path):
            for e in glob(str(file_path), recursive=True):
                self.add_file(Path(e))

        else:
            with file_path.open() as file_handle:
                entries = json.load(file_handle)

            if not isinstance(entries, list):
                raise ValueError
            for entry in entries:
                self._add_entry(entry)

    def _normalize_value(self, tag: str, value: Any) -> str:
        if isinstance(value, list):
            if len(value) == 1:
                (value,) = value
        if tag == "sub":
            value = normalize_subject(value)
        if not isinstance(value, str):
            raise ValueError
        return value

    def _add_entry(self, entry: Mapping[str, str]) -> None:
        rating_str: str | None = entry.get("rating")

        if rating_str is None:
            rating: Rating = Rating.NONE
        else:
            rating = Rating[rating_str.upper()]

        tags = pmap({tag: self._normalize_value(tag, value) for tag, value in entry.items() if tag != "rating"})

        self.index[tags].add(rating)
        if "type" in tags:
            self.types.add(tags["type"])

        self.relevant_tag_names.update(tags.keys())

    def iterate_ratings(self, tags: Mapping[str, str]) -> Iterator[Rating]:
        yield Rating.NONE  # Default value

        if "type" in tags:
            indices: Iterator[PMap] = map(pmap, powerset(tags.items()))
        else:
            indices = (
                subset.set("type", rating_type) for subset in map(pmap, powerset(tags.items())) for rating_type in self.types
            )

        for index in indices:
            if index in self.index:
                yield from self.index[index]

    def get(self, tags: Mapping[str, Any]) -> Decision:
        if len(self.relevant_tag_names) == 0:
            relevant_tags = pmap(tags)
        else:
            relevant_tags = pmap(
                {tag: self._normalize_value(tag, value) for tag, value in tags.items() if tag in self.relevant_tag_names}
            )

        rating: Rating = max(self.iterate_ratings(relevant_tags))

        if rating == Rating.BAD:
            return Decision.EXCLUDE
        elif rating == Rating.GOOD:
            return Decision.INCLUDE
        elif rating == Rating.NONE or rating == Rating.UNCERTAIN:
            if relevant_tags not in self.shown_warning_tags:
                logger.warning(
                    f"Will include observation ({format_tags(relevant_tags)}) for analysis "
                    f'even though quality rating is "{rating.name}"'
                )
                self.shown_warning_tags.add(relevant_tags)

            return Decision.INCLUDE
        else:
            raise ValueError()
