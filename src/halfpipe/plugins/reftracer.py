# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from pathlib import Path
from shutil import rmtree

from nipype.pipeline.engine.utils import load_resultfile

from ..logging import logger
from ..utils.path import find_paths, is_empty


class PathReferenceTracer:
    def __init__(self, workdir: str | Path):
        self.workdir: Path = self.resolve(workdir)
        self.weak_references: set[Path] = set()

        self.black: set[Path] = set()  # is pending
        self.grey: set[Path] = set()  # still has references from pending nodes
        self.white: set[Path] = set()

        self.refs: dict[Path, set[Path]] = defaultdict(set)  # other paths that are referenced by a path
        self.deps: dict[Path, set[Path]] = defaultdict(set)  # paths that a path depends on (inverse refs)

    def resolve(self, path) -> Path:
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

    def add_ref(self, from_path, to_path):
        if from_path == to_path:
            return

        self.refs[from_path].add(to_path)
        self.deps[to_path].add(from_path)

        if from_path in self.white:  # no longer without references
            self.white.remove(from_path)
            self.grey.add(from_path)

    def remove_ref(self, from_path, to_path):
        self.refs[from_path].remove(to_path)
        self.deps[to_path].remove(from_path)

        if len(self.refs[from_path]) == 0:  # no more references remain
            if from_path in self.grey:
                self.grey.remove(from_path)
                self.white.add(from_path)

    def node_resultfile_path(self, node) -> Path:
        to_path = self.resolve(node.output_dir())

        return to_path / f"result_{node.name}.pklz"

    def add_file(self, path, target=None):
        if target is None:
            target = self.white

        if path not in self.black and path not in self.grey and path not in self.white:
            target.add(path)

    def add_node(self, node):  # to black set
        path = self.node_resultfile_path(node)

        self.add_file(path, target=self.black)

        child = path
        while child.parent != self.workdir:
            parent = child.parent

            if child != path.parent:
                self.weak_references.add(child)

            self.add_file(parent)
            self.add_ref(parent, child)

            child = parent

    def set_node_pending(self, node):
        to_path = self.node_resultfile_path(node)

        if to_path not in self.deps:
            return

        if node.input_source:
            input_files, _ = zip(*node.input_source.values(), strict=False)
            for input_file in input_files:
                from_path = self.resolve(input_file)
                if from_path in self.black or from_path in self.grey:
                    self.add_ref(from_path, to_path)
                else:
                    logger.debug(f'{node.name} has untracked input_source "{input_file}"')

    def set_node_complete(self, node, unmark: bool):
        to_path = self.node_resultfile_path(node)

        if to_path not in self.deps:  # node is not being tracked
            return

        if to_path not in self.black:  # needs to be pending
            return

        deps = [*self.deps[to_path]]
        for from_path in deps:  # remove input dependencies after node was run
            if from_path == to_path.parent:
                continue

            self.remove_ref(from_path, to_path)

        if unmark is True:
            self.black.remove(to_path)
            if len(self.refs[to_path]) == 0:
                self.white.add(to_path)
                return  # no need to track result
            else:
                self.grey.add(to_path)

        try:
            result = load_resultfile(to_path)  # load result from file
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

                log_method(f'Memory usage for node "{node.fullname}" exceeds prediction ' f"{predicted=} {actual=}")

            elif predicted - actual > 5:  # more than 5 gigabytes error
                logger.warning(
                    f'Memory usage for node "{node.fullname}" is significantly below prediction ' f"{predicted=} {actual=}"
                )

        except Exception:
            pass

        stack = [*find_paths(result.outputs)]
        while len(stack) > 0:
            path = self.resolve(stack.pop())

            found = set(self.find(path))

            if len(found) == 0:
                continue  # this path is not being traced, for example because it is an external file

            self.add_file(path)
            self.add_ref(path, to_path)  # add reference from result file

            for from_path in found:
                self.add_ref(from_path, path)  # add any parents as dependency

            if path.is_dir():
                stack.extend(path.iterdir())

    def collect(self):
        while len(self.white) > 0:
            to_path = self.white.pop()

            deps = list(self.deps[to_path])

            for from_path in deps:  # remove input dependencies
                self.remove_ref(from_path, to_path)

            yield to_path

    def collect_and_delete(self):
        paths = list(self.collect())

        if len(paths) == 0:
            return

        logger.info("[node dependencies finished] removing\n" + "\n".join(map(str, paths)))

        for path in paths:
            if path in self.weak_references:
                if path.is_dir() and not is_empty(path):
                    continue  # do not delete non-empty weak references, in case other chunks refer to them

            rmtree(path, ignore_errors=True)
