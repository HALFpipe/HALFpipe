# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from dataclasses import dataclass
from pathlib import Path
from shelve import Shelf

from ..cache import cache_obj, uncache_obj


@dataclass(frozen=True)
class MockIdentifiable:
    uuid: str


def test_cache_uuid(tmp_path: Path):
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    uuid = "abcde"

    x = MockIdentifiable(uuid=uuid)

    cache_obj(workdir, "test", x)

    y = uncache_obj(workdir, "test", uuid=uuid)

    assert x == y


def test_cache_uuid_mismatch(tmp_path: Path):
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    uuid = "abcde"

    x = MockIdentifiable(uuid="12345")

    cache_obj(workdir, "test", x, uuid=uuid)

    y = uncache_obj(workdir, "test", uuid=uuid)

    assert y is None


def test_cache_mapping(tmp_path: Path):
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    uuid = "abcde"

    x = dict(a="a", b="b", c="c")

    cache_obj(workdir, "test", x, uuid=uuid)

    y = uncache_obj(workdir, "test", uuid=uuid)

    assert isinstance(y, Shelf)
