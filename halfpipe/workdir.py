# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Union

from pathlib import Path
from os.path import normpath

from .logging import Context as LoggingContext
from .hooks import run_hooks_from_dir


def init_workdir(workdir: Union[str, Path], fs_root: Union[str, Path] = None) -> Path:
    workdir = str(workdir)

    if fs_root is None:
        from calamities.config import Config as CalamitiesConfig
        fs_root = CalamitiesConfig.fs_root

    fs_root = str(fs_root)

    # resolve workdir in fs_root
    abspath = str(Path(workdir).resolve())

    if not abspath.startswith(fs_root):
        abspath = normpath(fs_root + abspath)

    workdir = Path(abspath)

    workdir.mkdir(parents=True, exist_ok=True)

    LoggingContext.setWorkdir(workdir)

    run_hooks_from_dir(workdir)

    return workdir
