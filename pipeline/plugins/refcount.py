# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from nipype.interfaces.base.support import InterfaceResult


def iterpath(path):
    for parent in reversed(path.parents):
        if len(parent.name) > 0:
            yield parent.name
    yield path.name


class ReferenceCounter:
    def __init__(self):
        self.files = {}
        self.sets = []

    def put(self, result, jobid=0):
        values = []
        stack = [result]
        while len(stack) > 0:
            obj = stack.pop()
            if isinstance(obj, InterfaceResult):
                stack.append(obj.outputs.__dict__)
            elif isinstance(obj, dict):
                stack.extend(obj.values())
            elif isinstance(obj, str):
                values.append(obj)
        for val in values:
            path = Path(val)
            if not path.exists():
                continue
            curfiles = self.files
            for elem in iterpath(path):
                if elem not in curfiles:
                    curfiles[elem] = {}
                curfiles = curfiles[elem]
            if 0 not in curfiles or not isinstance(curfiles[0], set):
                curfiles[0] = set()
                self.sets.append(curfiles[0])
            curfiles[0].add(jobid)

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
