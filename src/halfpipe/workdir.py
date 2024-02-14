# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from uuid import uuid4

from .logging.base import LoggingContext
from .utils.path import resolve


def init_workdir(workdir: str | Path, fs_root: str | Path | None = None) -> Path:
    workdir = str(workdir)

    if fs_root is None:
        from .ui.components.config import Config as UIConfig

        fs_root = UIConfig.fs_root

    fs_root = str(fs_root)

    workdir_path = resolve(workdir, fs_root)

    # Check permissions and file system compatibility
    try:
        workdir_path.mkdir(parents=True, exist_ok=True)

        uuid = str(uuid4())

        test_file_path_a = workdir_path / f".halfpipe-permission-test-a-{uuid}"
        test_file_path_a.touch(exist_ok=True)

        test_file_path_b = workdir_path / f".halfpipe-permission-test-b-{uuid}"
        test_file_path_b.symlink_to(test_file_path_a)

        test_file_path_b.unlink()
        test_file_path_a.unlink()
    except (PermissionError, OSError) as e:
        raise RuntimeError(
            f'Cannot use "{workdir}" as working directory for HALFpipe. '
            "Please check that you have sufficient permissions. "
            "Please also check that you are using a file system that supports symbolic links. "
            "For example, FAT32 and exFAT are incompatible."
        ) from e

    LoggingContext.set_workdir(workdir_path)

    return workdir_path
