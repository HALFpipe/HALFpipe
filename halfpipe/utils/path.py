# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
from pathlib import Path
from shutil import copyfile
from typing import Generator

from . import logger


def resolve(path: Path | str, fs_root: Path | str) -> Path:

    fs_root = str(fs_root)

    # resolve workdir in fs_root
    abspath = str(Path(path).resolve())

    if not abspath.startswith(fs_root):
        abspath = op.normpath(fs_root + abspath)

    return Path(abspath)


def find_paths(obj):
    from pathlib import Path

    from nipype.interfaces.base.specs import BaseTraitedSpec
    from nipype.interfaces.base.support import InterfaceResult

    paths = []
    stack = [obj]
    while len(stack) > 0:
        obj = stack.pop()
        if isinstance(obj, InterfaceResult):
            stack.append(obj.inputs)
            stack.append(obj.outputs)
        elif isinstance(obj, BaseTraitedSpec):
            stack.append(obj.get_traitsfree())
        elif hasattr(obj, "__dict__"):
            stack.append(obj.__dict__)
        elif isinstance(obj, dict):
            stack.extend(obj.values())
        elif isinstance(obj, str):
            if not obj.startswith("def") and Path(obj).exists():
                paths.append(obj)
        elif isinstance(obj, Path):
            if obj.exists():
                paths.append(obj)
        else:  # probably some kind of iterable
            try:
                stack.extend(obj)
            except TypeError:
                pass
    return paths


def split_ext(path: Path | str):
    """Splits filename and extension (.gz safe)
    >>> split_ext('some/file.nii.gz')
    ('file', '.nii.gz')
    >>> split_ext('some/other/file.nii')
    ('file', '.nii')
    >>> split_ext('otherext.tar.gz')
    ('otherext', '.tar.gz')
    >>> split_ext('text.txt')
    ('text', '.txt')

    Adapted from niworkflows
    """
    from pathlib import Path

    name = str(Path(path).name)

    safe_name = name
    for compound_extension in [".gz", ".xz"]:
        safe_name = safe_name.removesuffix(compound_extension)

    stem = Path(safe_name).stem
    return stem, name[len(stem) :]


def is_empty(path: Path | str) -> bool:
    from pathlib import Path

    path = Path(path)
    try:
        if next(path.iterdir()) is not None:  # dir is not empty
            return False
    except (FileNotFoundError, StopIteration):
        pass

    return True


def validate_workdir(path: Path | str):
    try:
        return Path(path).is_dir()
    except TypeError:
        return False


def is_hidden(path: Path | str) -> bool:
    """
    adapted from cpython glob
    """
    return Path(path).stem[0] == "."


def iterdir(dirname: str | Path, dironly: bool) -> Generator[str, None, None]:
    """
    adapted from cpython glob
    """
    if not dirname:
        dirname = os.curdir
    try:
        with os.scandir(dirname) as it:
            for entry in it:
                try:
                    if not dironly or entry.is_dir():
                        entry_name = entry.name
                        if entry.is_dir():
                            entry_name = op.join(entry_name, "")
                        if not is_hidden(entry_name):
                            yield entry_name
                except OSError:
                    pass
    except OSError:
        return


def rlistdir(
    dirname: str | Path,
    dironly: bool = False,
    maxdepth: int | None = None,
) -> Generator[str, None, None]:
    """
    adapted from cpython glob
    """

    if maxdepth is not None:
        maxdepth -= 1

    names = list(iterdir(dirname, dironly))
    for x in names:
        path = op.join(dirname, x) if dirname else x
        yield path

        if maxdepth is None or maxdepth > 0:
            yield from rlistdir(path, dironly)


def copy_if_newer(inpath: Path, outpath: Path):
    outpath.parent.mkdir(exist_ok=True, parents=True)
    if outpath.exists():
        if os.stat(inpath).st_mtime <= os.stat(outpath).st_mtime:
            logger.info(f'Not overwriting file "{outpath}"')
            return False
        logger.info(f'Overwriting file "{outpath}"')
    else:
        logger.info(f'Creating file "{outpath}"')
    copyfile(inpath, outpath)
    return True
