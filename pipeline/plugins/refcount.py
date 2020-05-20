# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from ..utils import findpaths


def iterpath(path):
    for parent in reversed(path.parents):
        if len(parent.name) > 0:
            yield parent.name
    yield path.name


class ReferenceCounter:
    def __init__(self):
        self.files = {}
        self.sets = []

    def addpath(self, path, jobid):
        curfiles = self.files
        for elem in iterpath(path.resolve()):
            if elem not in curfiles:
                curfiles[elem] = {}
            curfiles = curfiles[elem]
        if 0 not in curfiles or not isinstance(curfiles[0], set):
            curfiles[0] = set()
            self.sets.append(curfiles[0])
        curfiles[0].add(jobid)

    def put(self, result, jobid=0):
        paths = findpaths(result)
        while len(paths) > 0:
            path = Path(paths.pop())
            if path.is_dir():
                paths.extend(path.iterdir())
            else:
                self.addpath(path, jobid)

    def pop(self, jobid):
        for s in self.sets:
            if jobid in s:
                s.remove(jobid)

    def can_delete(self, path):
        if not isinstance(path, Path):
            path = Path(path)
        curfiles = self.files
        for elem in iterpath(path):
            if elem not in curfiles:
                return True
            curfiles = curfiles[elem]
        filesstack = [curfiles]
        while len(filesstack) > 0:
            files = filesstack.pop()
            for k, v in files.items():
                if k == 0:
                    if len(v) > 0:
                        return False
                else:
                    filesstack.append(v)
        return True
