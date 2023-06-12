# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Generator

from ..file_index.bids import BIDSIndex
from ..result.base import ResultDict
from ..result.bids.images import load_images
from ..utils.path import rlistdir


def find_derivatives_directories(
    name: str, path: Path | str, maxdepth: int = 1
) -> Generator[Path, None, None]:
    path = Path(path)
    if path.parts[-2:] == ("derivatives", name):
        yield path
        return
    if path.parts[-1] == "derivatives":
        path = path.parent
    if path.parts[-2] == "derivatives":
        path = path.parent.parent
    working_directories: set[Path] = set()
    for file_name in rlistdir(path, maxdepth=maxdepth):
        file_path = Path(file_name)
        if file_path.suffix == ".zip":
            continue
        if file_path.name == "spec.json":
            working_directories.add(file_path.parent)

    found_derivatives = False
    for working_directory in working_directories:
        derivatives_path = working_directory / "derivatives" / name
        if derivatives_path.is_dir():
            found_derivatives = True
            yield derivatives_path

    if not found_derivatives:
        yield path


def collect_halfpipe_derivatives(
    path: Path | str, maxdepth: int = 1
) -> list[ResultDict]:
    index = BIDSIndex()
    for derivatives_directory in find_derivatives_directories(
        "halfpipe", path, maxdepth=maxdepth
    ):
        index.put(derivatives_directory)

    results = load_images(index)

    return results
