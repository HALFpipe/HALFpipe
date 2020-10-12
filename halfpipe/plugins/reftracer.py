# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
import logging

from ..utils import findpaths

logger = logging.getLogger("halfpipe")


class PathReferenceTracer:
    def __init__(self):
        self.black = set()  # is pending
        self.grey = set()  # still has references from pending nodes
        self.white = set()

        self.refs = dict()  # other paths that depend on a path
        self.deps = dict()  # paths that a path depends on

    def resolve(self, path):
        if not isinstance(path, Path):
            path = Path(path)
        path = path.resolve()
        return path

    def find(self, path):
        path = self.resolve(path)
        pathset = set(path.parents)
        pathset.add(path)
        # yield any tracked folders that contain the target path
        yield from pathset & self.black
        yield from pathset & self.grey

    def add_ref(self, frompath, topath):
        self.refs[frompath].add(topath)
        if frompath in self.white:  # no longer without references
            self.white.remove(frompath)
            self.grey.add(frompath)
        self.deps[topath].add(frompath)

    def remove_ref(self, frompath, topath):
        self.refs[frompath].remove(topath)
        if len(self.refs[frompath]) == 0:  # no more references remain
            if frompath in self.grey:
                self.grey.remove(frompath)
                self.white.add(frompath)
        self.deps[topath].remove(frompath)

    def add_node(self, node):  # to black set
        path = self.resolve(node.output_dir())
        self.black.add(path)
        self.refs[path] = set()  # initialize empty
        self.deps[path] = set()

    def set_node_pending(self, node):
        topath = self.resolve(node.output_dir())

        if topath not in self.deps:
            return

        if node.input_source:
            input_files, _ = zip(*node.input_source.values())
            for input_file in input_files:
                for frompath in self.find(input_file):
                    self.add_ref(frompath, topath)

    def set_node_complete(self, node, unmark):
        topath = self.resolve(node.output_dir())

        if topath not in self.deps:
            return

        deps = [*self.deps[topath]]
        for frompath in deps:  # remove input dependencies
            self.remove_ref(frompath, topath)

        if unmark is True:
            self.black.remove(topath)
            if len(self.refs[topath]) == 0:
                self.white.add(topath)
            else:
                self.grey.add(topath)

        try:
            result = node.result  # load result from file
        except Exception as ex:
            logger.info(f"Node {node} does not have result: ", ex)
            return

        stack = [*findpaths(result)]
        while len(stack) > 0:
            path = self.resolve(stack.pop())

            found = set(self.find(path))

            if len(found) == 0:
                continue  # this path is not being traced, for example because it is an external file

            for frompath in found:
                self.add_ref(frompath, topath)  # add result file as dependency

            if path.is_dir():
                stack.extend(path.iterdir())

    def collect(self):
        while len(self.white) > 0:
            topath = self.white.pop()
            deps = [*self.deps[topath]]
            for frompath in deps:  # remove input dependencies
                self.remove_ref(frompath, topath)
            yield topath
