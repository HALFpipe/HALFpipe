# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from nipype.pipeline.engine.utils import load_resultfile

from ..utils import logger
from ..utils.path import find_paths


class PathReferenceTracer:
    def __init__(self):
        self.black = set()  # is pending
        self.grey = set()  # still has references from pending nodes
        self.white = set()

        self.refs = dict()  # other paths that are referenced by a path
        self.deps = dict()  # paths that a path depends on (inverse refs)

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
        if frompath == topath:
            return

        self.refs[frompath].add(topath)
        self.deps[topath].add(frompath)

        if frompath in self.white:  # no longer without references
            self.white.remove(frompath)
            self.grey.add(frompath)

    def remove_ref(self, frompath, topath):
        self.refs[frompath].remove(topath)
        self.deps[topath].remove(frompath)

        if len(self.refs[frompath]) == 0:  # no more references remain
            if frompath in self.grey:
                self.grey.remove(frompath)
                self.white.add(frompath)

    def node_resultfile_path(self, node) -> Path:
        topath = self.resolve(node.output_dir())

        return topath / f"result_{node.name}.pklz"

    def add_file(self, path, target=None):
        if target is None:
            target = self.white

        if path not in self.black and path not in self.grey and path not in self.white:
            target.add(path)

        if path not in self.refs:
            self.refs[path] = set()  # initialize empty

        if path not in self.deps:
            self.deps[path] = set()

    def add_node(self, node):  # to black set
        path = self.node_resultfile_path(node)

        self.add_file(path, target=self.black)
        self.add_file(path.parent)  # also track node dir

        self.add_ref(path.parent, path)  # cannot delete dir with files in it

    def set_node_pending(self, node):
        topath = self.node_resultfile_path(node)

        if topath not in self.deps:
            return

        if node.input_source:
            input_files, _ = zip(*node.input_source.values())
            for input_file in input_files:
                frompath = self.resolve(input_file)
                if frompath in self.black or frompath in self.grey:
                    self.add_ref(frompath, topath)
                else:
                    logger.debug(
                        f'{node.name} has untracked input_source "{input_file}"'
                    )

    def set_node_complete(self, node, unmark: bool):
        topath = self.node_resultfile_path(node)

        if topath not in self.deps:  # node is not being tracked
            return

        if topath not in self.black:  # needs to be pending
            return

        deps = [*self.deps[topath]]
        for frompath in deps:  # remove input dependencies after node was run
            if frompath == topath.parent:
                continue

            self.remove_ref(frompath, topath)

        if unmark is True:
            self.black.remove(topath)
            if len(self.refs[topath]) == 0:
                self.white.add(topath)
                return  # no need to track result
            else:
                self.grey.add(topath)

        try:
            result = load_resultfile(topath)  # load result from file
        except Exception as ex:
            logger.info(f"{node.name} does not have result: %s", ex)
            return

        try:
            actual = result.runtime.mem_peak_gb
            predicted = node.mem_gb

            if actual - predicted > 0:

                log_method = logger.info
                if actual - predicted > 1:  # more than one gigabyte error
                    log_method = logger.warning

                log_method(
                    f'Memory usage for node "{node.fullname}" exceeds prediction '
                    f"{predicted=} {actual=}"
                )

            elif predicted - actual > 5:  # more than 5 gigabytes error
                logger.warning(
                    f'Memory usage for node "{node.fullname}" is significantly below prediction '
                    f"{predicted=} {actual=}"
                )

        except Exception:
            pass

        stack = [*find_paths(getattr(result, "outputs"))]
        while len(stack) > 0:
            path = self.resolve(stack.pop())

            found = set(self.find(path))

            if len(found) == 0:
                continue  # this path is not being traced, for example because it is an external file

            self.add_file(path)
            self.add_ref(path, topath)  # add reference from result file

            for frompath in found:
                self.add_ref(frompath, path)  # add any parents as dependency

            if path.is_dir():
                stack.extend(path.iterdir())

    def collect(self):
        while len(self.white) > 0:
            topath = self.white.pop()
            deps = [*self.deps[topath]]
            for frompath in deps:  # remove input dependencies
                self.remove_ref(frompath, topath)
            yield topath
