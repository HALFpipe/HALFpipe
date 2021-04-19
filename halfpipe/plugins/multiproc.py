# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import gc
import logging
import shutil
from stackprinter import format_current_exception

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

from nipype.pipeline import plugins as nip
from nipype.utils.profiler import get_system_total_memory_gb

from matplotlib import pyplot as plt

from .reftracer import PathReferenceTracer
from ..logging import Context

logger = logging.getLogger("nipype.workflow")


def initializer(workdir, loggingargs, watchdog, host_env):
    from ..logging import setup as setuplogging
    setuplogging(**loggingargs)

    if watchdog is True:
        from ..watchdog import init_watchdog

        init_watchdog()

    os.environ.update(host_env)

    os.chdir(workdir)


# Run node
def run_node(node, updatehash, taskid):
    """Function to execute node.run(), catch and log any errors and
    return the result dictionary
    Parameters
    ----------
    node : nipype Node instance
        the node to run
    updatehash : boolean
        flag for updating hash
    taskid : int
        an identifier for this task
    Returns
    -------
    result : dictionary
        dictionary containing the node runtime results and stats
    """

    # Init variables
    result = dict(result=None, traceback=None, taskid=taskid)

    # Try and execute the node via node.run()
    try:
        result["result"] = node.run(updatehash=updatehash)
    except Exception:  # catch all here
        result["traceback"] = format_current_exception()
        result["result"] = node.result

    # Avoid matplotlib memory leak
    plt.close("all")
    gc.collect()

    # Return the result dictionary
    return result


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

        mp_context = mp.get_context("forkserver")  # force forkserver
        self.pool = ProcessPoolExecutor(
            max_workers=self.processors,
            initializer=initializer,
            initargs=(
                self._cwd,
                Context.loggingargs(),
                plugin_args.get("watchdog", False),
                dict(os.environ),
            ),
            mp_context=mp_context,
        )

        self._stats = None
        self._keep = plugin_args.get("keep", "all")
        if self._keep != "all":
            self._rt = PathReferenceTracer()

    def _postrun_check(self):
        self.pool.shutdown(wait=False)  # do not block

    def _submit_job(self, node, updatehash=False):
        self._taskid += 1

        # Don't allow streaming outputs
        if getattr(node.interface, "terminal_output", "") == "stream":
            node.interface.terminal_output = "allatonce"

        result_future = self.pool.submit(run_node, node, updatehash, self._taskid)
        result_future.add_done_callback(self._async_callback)
        self._task_obj[self._taskid] = result_future

        logger.debug(
            "[MultiProc] Submitted task %s (taskid=%d).", node.fullname, self._taskid
        )
        return self._taskid

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
            if hasattr(self.procs[jobid], "keep") and self.procs[jobid].keep is True:
                unmark = False  # always keep feature outputs
            self._rt.set_node_complete(self.procs[jobid], unmark)
        super(MultiProcPlugin, self)._task_finished_cb(jobid, cached=cached)

    def _async_callback(self, args):
        try:
            result = args.result()
            self._taskresult[result["taskid"]] = result
        except Exception as e:
            logging.getLogger("halfpipe").exception(f"Exception for {args}: %s", e)

    def _remove_node_dirs(self):
        """Removes directories whose outputs have already been used up
        """
        if self._rt is not None:
            paths = [*self._rt.collect()]
            if len(paths) > 0:
                logger.info("[node dependencies finished] removing\n" + "\n".join(map(str, paths)))
                for path in paths:
                    shutil.rmtree(path, ignore_errors=True)
