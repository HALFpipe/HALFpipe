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
        if not isinstance(path, Path):
            path = Path(path)

        curfiles = self.files
        for elem in iterpath(path.resolve()):
            if elem not in curfiles:
                curfiles[elem] = {}
            curfiles = curfiles[elem]

        if None not in curfiles or not isinstance(curfiles[None], set):
            curfiles[None] = set()  # None key is the jobid set
            self.sets.append(curfiles[None])
        curfiles[None].add(jobid)

    def put(self, result, jobid=0):
        for path in findpaths(result):
            self.addpath(path, jobid)

    def pop(self, jobid):
        for s in self.sets:
            if jobid in s:
                s.remove(jobid)

    def can_delete(self, path):
        if not isinstance(path, Path):
            path = Path(path)

        curfiles = self.files
        for elem in iterpath(path):  # traverse the parents of the path
            if elem not in curfiles:
                return True  # the file is not being tracked

            if None in curfiles:   # None key is the jobid set
                if len(curfiles[None]) > 0:  # there are still dependent jobids
                    return False

            curfiles = curfiles[elem]

        filesstack = [curfiles]
        while len(filesstack) > 0:  # traverse the children of the path
            curfiles = filesstack.pop()

            if None in curfiles:
                if len(curfiles[None]) > 0:  # as before
                    return False

            for k, v in curfiles.items():
                if k is not None:
                    filesstack.append(v)  # subfolders or files

        return True
