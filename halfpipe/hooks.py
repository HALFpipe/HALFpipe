# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import posixpath
import sys
from pathlib import Path
from typing import List, Union
from zipfile import ZipFile
from zipimport import zipimporter

from .utils import logger


class ZipPath:
    # based on cpython

    def __init__(self, root: ZipFile, at: str = ""):
        self.root = root
        self.namelist = frozenset(root.namelist())
        self.at: str = at

    def __str__(self):
        assert self.root.filename is not None
        return posixpath.join(self.root.filename, self.at)

    @property
    def name(self):
        return posixpath.basename(self.at.rstrip("/"))

    @property
    def parent(self):
        parent_at = posixpath.dirname(self.at.rstrip("/"))
        if parent_at:
            parent_at += "/"
        return self._next(parent_at)

    def _is_child(self, path):
        return posixpath.dirname(path.at.rstrip("/")) == self.at.rstrip("/")

    def _next(self, at):
        return ZipPath(self.root, at)

    def is_dir(self):
        return not self.at or self.at.endswith("/")

    def is_file(self):
        return not self.is_dir()

    def exists(self):
        return self.at in self.namelist

    def iterdir(self):
        if not self.is_dir():
            raise ValueError("Can't listdir a file")
        subs = map(self._next, self.namelist)
        return filter(self._is_child, subs)

    def joinpath(self, add):
        next = posixpath.join(self.at, add)
        if next not in self.namelist:
            if (next + "/") in self.namelist:
                next += "/"  # is dir
        return self._next(next)

    __truediv__ = joinpath


def run_hooks_from_dir(workdir: Path):
    plugins = []

    stack: List[Union[Path, ZipPath]] = [workdir]
    zip_files: List[ZipFile] = []
    while len(stack) > 0:
        parent = stack.pop()
        for child in parent.iterdir():
            if parent == workdir:
                if child.name in [
                    "nipype",
                    "grouplevel",
                    "derivatives",
                    "rawdata",
                    "reports",
                ]:
                    continue  # known workdir subdirs
            if child.is_dir():
                if (child / "__init__.py").exists():  # candidate dir is a module
                    plugins.append(child)
            elif isinstance(child, Path) and child.suffix == ".zip":
                try:
                    zip_file = ZipFile(child)
                    zip_files.append(zip_file)

                    zip_path = ZipPath(zip_file)
                    stack.append(zip_path)
                except Exception as e:
                    logger.warning(
                        f'Cannot list file "{child}": %s', e, stack_info=True
                    )
            elif str(child).endswith(".py"):
                plugins.append(child)

    for plugin in plugins:
        module = None
        if isinstance(plugin, Path):
            # based on https://github.com/nipy/heudiconv/blob/master/heudiconv/utils.py#L314
            plugin_path = plugin.absolute()
            path = str(plugin_path.parent)
            module_name = plugin_path.stem
            old_syspath = sys.path[:]
            try:
                sys.path.insert(0, path)
                module = __import__(module_name)
            finally:
                sys.path = old_syspath
        elif isinstance(plugin, ZipPath):
            zi = zipimporter(str(plugin.parent))
            module = zi.load_module(plugin.name)

        if module is not None:
            hook = getattr(module, "hook", None)
            if hook is not None:
                hook()

    for zip_file in zip_files:
        zip_file.close()
