# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Generator, Iterable

from ..file_index.bids import BIDSIndex
from ..result.base import ResultDict
from ..result.bids.images import load_images
from ..utils.path import AnyPath, recursive_list_directory


def find_derivatives_directories(name: str, path: str | AnyPath, max_depth: int = 1) -> Generator[AnyPath, None, None]:
    if isinstance(path, str):
        path = Path(path)
    if isinstance(path, Path):
        if path.parts[-2:] == ("derivatives", name):
            yield path
            return
        if path.parts[-1] == "derivatives":
            path = path.parent
        if path.parts[-2] == "derivatives":
            path = path.parent.parent
    working_directories: set[Path] = set()
    for file_path in recursive_list_directory(path, max_depth=max_depth):
        if file_path.name == "spec.json":
            working_directories.add(file_path.parent)  # type: ignore

    found_derivatives = False
    for working_directory in working_directories:
        derivatives_path = working_directory / "derivatives" / name
        if derivatives_path.is_dir():
            found_derivatives = True
            yield derivatives_path

    if not found_derivatives:
        yield path


def collect_halfpipe_derivatives(paths: Iterable[str | AnyPath], max_depth: int = 1, num_threads: int = 1) -> list[ResultDict]:
    index = BIDSIndex()
    for path in paths:
        for derivatives_directory in find_derivatives_directories("halfpipe", path, max_depth=max_depth):
            index.put(derivatives_directory)

    results = load_images(index, num_threads=num_threads)

    return results
