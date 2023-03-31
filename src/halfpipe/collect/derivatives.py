# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from ..file_index.bids import BIDSIndex
from ..result.bids.images import load_images
from ..utils.path import rlistdir


def collect_derivatives(path: Path, maxdepth: int = 3):
    index = BIDSIndex()
    if path.parts[-2:] == ("derivatives", "halfpipe"):
        index.put(path)
    else:
        working_directories: set[Path] = set()

        for file_name in rlistdir(path, maxdepth=maxdepth):
            file_path = Path(file_name)

            if file_path.suffix == ".zip":
                continue

            if file_path.name == "spec.json":
                working_directories.add(file_path.parent)

        for working_directory in working_directories:
            derivatives_path = working_directory / "derivatives" / "halfpipe"
            index.put(derivatives_path)

        if len(working_directories) == 0:
            index.put(path)

    results = load_images(index)

    return results
