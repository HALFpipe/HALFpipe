# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os.path import normpath
from pathlib import Path


def resolve(path: Path | str, fs_root: Path | str) -> Path:

    fs_root = str(fs_root)

    # resolve workdir in fs_root
    abspath = str(Path(path).resolve())

    if not abspath.startswith(fs_root):
        abspath = normpath(fs_root + abspath)

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
