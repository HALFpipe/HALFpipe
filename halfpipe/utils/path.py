# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def resolve(path, fs_root):
    from pathlib import Path
    from os.path import normpath

    fs_root = str(fs_root)

    # resolve workdir in fs_root
    abspath = str(Path(path).resolve())

    if not abspath.startswith(fs_root):
        abspath = normpath(fs_root + abspath)

    return Path(abspath)


def findpaths(obj):
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


def splitext(fname):
    """Splits filename and extension (.gz safe)
    >>> splitext('some/file.nii.gz')
    ('file', '.nii.gz')
    >>> splitext('some/other/file.nii')
    ('file', '.nii')
    >>> splitext('otherext.tar.gz')
    ('otherext', '.tar.gz')
    >>> splitext('text.txt')
    ('text', '.txt')

    Source: niworkflows
    """
    from pathlib import Path

    basename = str(Path(fname).name)
    stem = Path(basename.rstrip(".gz")).stem
    return stem, basename[len(stem) :]
