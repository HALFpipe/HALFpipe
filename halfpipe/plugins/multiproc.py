# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import logging
import shutil

from nipype.pipeline import plugins as nip
from nipype.utils.profiler import get_system_total_memory_gb

from .reftracer import PathReferenceTracer
from ..logger import Logger
from ..watchdog import start_watchdog_daemon

logger = logging.getLogger("nipype.workflow")


def initializer(workdir, debug, verbose, watchdog):
    Logger.setup(workdir, debug=debug, verbose=verbose)
    if watchdog is True:
        start_watchdog_daemon()

    os.chdir(workdir)


class MultiProcPlugin(nip.MultiProcPlugin):
    def __init__(self, plugin_args=None):
        # Init variables and instance attributes
        super(nip.MultiProcPlugin, self).__init__(plugin_args=plugin_args)
        self._taskresult = {}
        self._task_obj = {}
        self._taskid = 0
        self._rt = None

        # Cache current working directory and make sure we
        # change to it when workers are set up
        self._cwd = plugin_args.get("workdir", os.getcwd())

        # Read in options or set defaults.
        self.processors = self.plugin_args.get("n_procs", mp.cpu_count())
        self.memory_gb = self.plugin_args.get(
            "memory_gb", get_system_total_memory_gb() * 0.9,  # Allocate 90% of system memory
        )
        self.raise_insufficient = self.plugin_args.get("raise_insufficient", True)

        # Instantiate different thread pools for non-daemon processes
        logger.debug(
            "[MultiProc] Starting (n_procs=%d, " "mem_gb=%0.2f, cwd=%s)",
            self.processors,
            self.memory_gb,
            self._cwd,
        )

        debug = plugin_args.get("debug", False)
        verbose = plugin_args.get("verbose", False)
        watchdog = plugin_args.get("watchdog", False)

        mp_context = mp.get_context("forkserver")  # force forkserver
        self.pool = ProcessPoolExecutor(
            max_workers=self.processors,
            initializer=initializer,
            initargs=(self._cwd, debug, verbose, watchdog),
            mp_context=mp_context,
        )

        self._stats = None
        self._keep = plugin_args.get("keep", "all")
        if self._keep != "all":
            self._rt = PathReferenceTracer()

    def _generate_dependency_list(self, graph):
        if self._rt is not None:
            for node in graph.nodes:
                self._rt.add_node(node)
            for node in graph.nodes:
                self._rt.set_node_pending(node)
        super(MultiProcPlugin, self)._generate_dependency_list(graph)

    def _task_finished_cb(self, jobid, cached=False):
        if self._rt is not None:
            name = self.procs[jobid].fullname
            unmark = True  # try to delete this when dependencies finish
            if self._keep == "some" and "fmriprep_wf" in name:
                unmark = False  # keep fmriprep if keep is "some"
            if self._keep == "some" and "ica_aroma_components_wf" in name:
                unmark = False
            if "features_wf" in name and "datasink" in name:
                unmark = False  # always keep feature outputs
            self._rt.set_node_complete(self.procs[jobid], unmark)
        super(MultiProcPlugin, self)._task_finished_cb(jobid, cached=cached)

    def _remove_node_dirs(self):
        """Removes directories whose outputs have already been used up
        """
        if self._rt is not None:
            for path in self._rt.collect():
                logger.info(f"[node dependencies finished] removing directory {str(path)}")
                shutil.rmtree(path, ignore_errors=True)
