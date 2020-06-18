# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import logging
import shutil

import numpy as np

from nipype.pipeline import plugins as nip
from nipype.utils.profiler import get_system_total_memory_gb

from .refcount import ReferenceCounter
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
        self._rc = ReferenceCounter()

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

    def _task_finished_cb(self, jobid, cached=False):
        try:
            self._rc.put(self.procs[jobid].result, jobid=jobid)
        except Exception:
            pass  # node doesn't have a result
        super(MultiProcPlugin, self)._task_finished_cb(jobid, cached=cached)

    def _async_callback(self, args):
        try:
            result = args.result()
            self._taskresult[result["taskid"]] = result
        except Exception as e:
            logging.getLogger("pipeline").exception(f"Exception for {args}: %s", e)

    def _remove_node_dirs(self):
        """Removes directories whose outputs have already been used up
        """
        if self._keep == "all":
            return
        indices = np.nonzero((self.refidx.sum(axis=1) == 0).__array__())[0]
        for idx in indices:
            if idx in self.mapnodesubids:
                continue
            if self.proc_done[idx] and (not self.proc_pending[idx]):
                name = self.procs[idx].fullname
                if self._keep == "some" and "preproc_wf" in name:
                    continue  # keep fmriprep if keep is "some"
                if "outputnode" in name:
                    continue  # always keep outputs
                self.refidx[idx, idx] = -1
                outdir = self.procs[idx].output_dir()
                self._rc.pop(idx)
                if not self._rc.can_delete(outdir):
                    continue
                logger.info(
                    ("[node dependencies finished] " "removing node: %s from directory %s")
                    % (self.procs[idx]._id, outdir)
                )
                shutil.rmtree(outdir, ignore_errors=True)
