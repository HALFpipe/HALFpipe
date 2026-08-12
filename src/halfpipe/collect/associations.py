# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""Tag-based association queries over the :class:`Database` index."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from ..model.tags import entities

if TYPE_CHECKING:
    from ..ingest.database import Database


def associations(database: Database, tags: Mapping[str, str] | None, **filters: str) -> tuple[str, ...] | None:
    """Find the files matching ``filters`` that are most closely associated with ``tags``.

    Starting from all files matching ``filters``, narrow by each shared tag from
    highest- to lowest-priority entity, returning the smallest non-empty set of files.
    """
    if tags is None:
        tags = dict()
    matching_files = database.get(**filters)
    for entity in reversed(entities):  # from high to low priority
        value = tags.get(entity)
        if value is None:
            continue
        files = database.filter(matching_files, **{entity: value})
        if len(files) > 0:
            matching_files = files
        if len(files) == 1:
            break
    if len(matching_files) > 0:
        return tuple(matching_files)
    return None


def _split_intended_for(pivot: str) -> tuple[str, str | None]:
    """Split a ``"entity.value"`` intended for string; ``"null"`` means the entity is absent."""
    entity, _, value = pivot.partition(".")
    return entity, None if value == "null" else value


def intended_for_targets(database: Database, fmap_path: str) -> set[str] | None:
    """Concrete paths a field map can be used for. A None results means
    that no metadata was found to determine the targets.
    """
    targets = database.resolved_spec.intended_for_by_filepaths.get(fmap_path)
    if targets is not None:
        return targets

    fmap_fileobj = database.fileobj(fmap_path)
    if fmap_fileobj is None:
        return None
    pivots = fmap_fileobj.intended_for
    if not pivots:
        return None

    fmap_tags = database.tags(fmap_path) or dict()
    sub = fmap_tags.get("sub")
    resolved: set[str] = set()
    for fmap_key, bold_keys in pivots.items():
        from_entity, from_value = _split_intended_for(fmap_key)
        if fmap_tags.get(from_entity) != from_value:
            continue
        for bold_key in bold_keys:
            to_entity, to_value = _split_intended_for(bold_key)
            if to_value is None:
                continue
            filters = {"datatype": "func", "suffix": "bold", to_entity: to_value}
            if sub is not None:
                filters["sub"] = sub
            resolved |= database.get(**filters)
    return resolved
