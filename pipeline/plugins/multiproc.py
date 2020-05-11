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
from nipype.utils.misc import str2bool

from pipeline.logger import Logger

logger = logging.getLogger("nipype.workflow")


def initializer(workdir, debug, verbose):
    Logger.setup(workdir, debug=debug, verbose=verbose)

    os.chdir(workdir)


class MultiProcPlugin(nip.MultiProcPlugin):
    def __init__(self, plugin_args=None):
        # Init variables and instance attributes
        super(nip.MultiProcPlugin, self).__init__(plugin_args=plugin_args)
        self._taskresult = {}
        self._task_obj = {}
        self._taskid = 0

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
        logging.getLogger("pipeline").debug(
            "[MultiProc] Starting (n_procs=%d, " "mem_gb=%0.2f, cwd=%s)",
            self.processors,
            self.memory_gb,
            self._cwd,
        )

        debug = plugin_args.get("debug", False)
        verbose = plugin_args.get("verbose", False)

        mp_context = mp.get_context("forkserver")  # force forkserver
        self.pool = ProcessPoolExecutor(
            max_workers=self.processors,
            initializer=initializer,
            initargs=(self._cwd, debug, verbose),
            mp_context=mp_context,
        )

        self._stats = None

    def _async_callback(self, args):
        try:
            result = args.result()
            self._taskresult[result["taskid"]] = result
        except Exception as e:
            logging.getLogger("pipeline").exception(f"Exception for {args}: %s", e)

    def _remove_node_dirs(self):
        """Removes directories whose outputs have already been used up
        """
        if str2bool(self._config["execution"]["remove_node_directories"]):
            indices = np.nonzero((self.refidx.sum(axis=1) == 0).__array__())[0]
            for idx in indices:
                if idx in self.mapnodesubids:
                    continue
                if self.proc_done[idx] and (not self.proc_pending[idx]):
                    if (
                        "anat_preproc_wf" in self.procs[idx].fullname
                        or "func_preproc_wf" in self.procs[idx].fullname
                    ):
                        continue  # keep some nodes because this is not safe
                    self.refidx[idx, idx] = -1
                    outdir = self.procs[idx].output_dir()
                    logger.info(
                        ("[node dependencies finished] " "removing node: %s from directory %s")
                        % (self.procs[idx]._id, outdir)
                    )
                    shutil.rmtree(outdir)
