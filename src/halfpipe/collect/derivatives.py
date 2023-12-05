# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Generator, Iterable

from ..file_index.bids import BIDSIndex
from ..result.base import ResultDict
from ..result.bids.images import load_images
from ..utils.path import AnyPath, recursive_list_directory


def find_derivatives_directories(
    name: str, path: str | AnyPath, max_depth: int = 1
) -> Generator[AnyPath, None, None]:
    """
    Browse the directory structure to find directories containing derivatives.

    The search starts from the specified path and looks for directories
    named "derivatives" that contain the specified name. The function then returns paths to these
    derivative directories.

    Parameters
    ----------
    name : str
        The name of the derivatives directory to search for.
    path : str or AnyPath
        The starting path for the search.
    max_depth : int, optional
        The maximum depth to search for derivative directories, by default 1.

    Returns
    -------
    Generator[AnyPath, None, None]
        Yields paths to derivative directories.
    """
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


def collect_halfpipe_derivatives(
    paths: Iterable[str | AnyPath], max_depth: int = 1, num_threads: int = 1
) -> list[ResultDict]:
    """
    Collects Halfpipe derivatives from specified paths.

    Halfpipe derivatives are collected by searching for directories with
    the name "halfpipe" within the provided paths. The function then populates a BIDSIndex with the
    found derivatives and loads images from the index.

    Parameters
    ----------
    paths : Iterable[str or AnyPath]
        Iterable of paths to search for Halfpipe derivatives.
    max_depth : int, optional
        The maximum depth to search for derivative directories, by default 1.
    num_threads : int, optional
        The number of threads to use for loading images, by default 1.

    Returns
    -------
    list[ResultDict]
        A list of ResultDict objects representing the collected Halfpipe derivatives.
    """
    index = BIDSIndex()
    for path in paths:
        for derivatives_directory in find_derivatives_directories(
            "halfpipe", path, max_depth=max_depth
        ):
            index.put(derivatives_directory)

    results = load_images(index, num_threads=num_threads)

    return results
