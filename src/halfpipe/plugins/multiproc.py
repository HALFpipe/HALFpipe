# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import gc
import os
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from threading import Thread
from typing import Any

import nipype.pipeline.engine as pe
from matplotlib import pyplot as plt
from nipype.pipeline import plugins as nip
from nipype.utils.gpu_count import gpu_count
from nipype.utils.profiler import get_system_total_memory_gb
from stackprinter import format_current_exception

from ..logging import logger
from ..utils.multiprocessing import get_init_args, mp_context
from .reftracer import PathReferenceTracer
import psutil
import gc
from copy import deepcopy
from traceback import format_exception
import numpy as np
from nipype.pipeline.engine.nodes import MapNode

try:
    from textwrap import indent
except ImportError:

    def indent(text, prefix):
        """A textwrap.indent replacement for Python < 3.3"""
        if not prefix:
            return text
        splittext = text.splitlines(True)
        return prefix + prefix.join(splittext)

SEQUENTIAL_MODE_THRESHOLD_GB = 1.5
RECOVERY_THRESHOLD_GB = 2.0


def initializer(
    init_args: tuple[set[int], dict[str, Any], dict[str, str], str],
    plugin_args: dict,
) -> None:
    from ..utils.multiprocessing import initializer

    initializer(*init_args)

    from ..utils.pickle import patch_nipype_unpickler

    patch_nipype_unpickler()

    watchdog = plugin_args.get("watchdog", False)
    if watchdog is True:
        from ..watchdog import init_watchdog

        init_watchdog()

    resource_monitor = plugin_args.get("resource_monitor", False)
    if resource_monitor is True:
        import nipype

        nipype.config.enable_resource_monitor()


# Run node
def run_node(node: pe.Node, updatehash: bool, taskid: int):
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
    result: dict[str, Any] = dict(result=None, traceback=None, taskid=taskid)

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
    def __init__(self, plugin_args: dict):
        # Init variables and instance attributes
        super(nip.MultiProcPlugin, self).__init__(plugin_args=plugin_args)
        self._taskresult: dict = dict()
        self._task_obj: dict = dict()
        self._taskid = 0
        self._rt = None

        # Cache current working directory and make sure we
        # change to it when workers are set up
        self._cwd: str = plugin_args.get("workdir", os.getcwd())

        # Read in options or set defaults.
        self.processors = self.plugin_args.get("n_procs", cpu_count())
        self.memory_gb = self.plugin_args.get(
            "memory_gb",
            get_system_total_memory_gb() * 0.9,  # Allocate 90% of system memory
        )
        self.raise_insufficient = self.plugin_args.get("raise_insufficient", True)

        # GPU handling for compatibility with Nipype ≥1.10
        self.n_gpus_visible = gpu_count()  # default is the available GPUs
        self.n_gpu_procs = plugin_args.get("n_gpu_procs", self.n_gpus_visible)  # allow to override by user

        # Instantiate different thread pools for non-daemon processes
        logger.debug(
            "[MultiProc] Starting (n_procs=%d, n_gpu_procs=%d, mem_gb=%0.2f, cwd=%s)",
            self.processors,
            self.n_gpu_procs,
            self.memory_gb,
            self._cwd,
        )

        self.pool = ProcessPoolExecutor(
            max_workers=self.processors,
            initializer=initializer,  # type: ignore
            initargs=(get_init_args(), plugin_args),  # type: ignore
            mp_context=mp_context,
        )

        self._stats = None
        self._keep = plugin_args.get("keep", "all")
        if self._keep != "all":
            self._rt = PathReferenceTracer(self._cwd)

        self._sequential_mode = False

    def _postrun_check(self):
        shutdown_thread = Thread(target=self.pool.shutdown, kwargs=dict(wait=True), daemon=True)
        shutdown_thread.start()
        shutdown_thread.join(timeout=10)
        if shutdown_thread.is_alive():
            logger.warning(
                "Shutdown of ProcessPoolExecutor timed out. This may lead to errors "
                "when the program closes. These error messages can usually be ignored"
            )

    def _check_resources(self, running_tasks):
        """
        Make sure there are resources available
        """
        free_memory_gb = self.memory_gb
        free_processors = self.processors
        for _, jobid in running_tasks:
            free_memory_gb -= min(self.procs[jobid].mem_gb, free_memory_gb)
            free_processors -= min(self.procs[jobid].n_procs, free_processors)

        return free_memory_gb, free_processors

    def _send_procs_to_workers(self, updatehash=False, graph=None):
        """
        Sends jobs to workers when system resources are available.
        Dynamically switches between parallel and sequential mode based on memory.
        """
        # Check to see if a job is available (jobs with all dependencies run)
        # See https://github.com/nipy/nipype/pull/2200#discussion_r141605722
        # See also https://github.com/nipy/nipype/issues/2372
        jobids = np.flatnonzero(
            ~self.proc_done & (self.depidx.sum(axis=0) == 0).__array__()
        )


        free_memory_gb, free_processors = self._check_resources(self.pending_tasks)
        # Accurate memory + CPU check
        free_real_memory_gb = psutil.virtual_memory().available / (1024 ** 3)


        # Switch between sequential and multiproc mode
        if not getattr(self, "_sequential_mode", False) and free_memory_gb < SEQUENTIAL_MODE_THRESHOLD_GB:
            self._sequential_mode = True
            logger.warning("[MultiProc] ⚠️ Low memory (< %.2f GB). Switching to SEQUENTIAL mode.", SEQUENTIAL_MODE_THRESHOLD_GB)
        elif getattr(self, "_sequential_mode", False) and free_memory_gb > RECOVERY_THRESHOLD_GB:
            self._sequential_mode = False
            logger.info("[MultiProc] 🧠 Memory freed (> %.2f GB). Switching back to MULTIPROCESSING.", RECOVERY_THRESHOLD_GB)


        stats = (
          len(self.pending_tasks),
          len(jobids),
          free_memory_gb,
          self.memory_gb,
          free_processors,
          self.processors,
        )
        if self._stats != stats:
            tasks_list_msg = ""

        
            running_tasks = [
                "  * %s" % self.procs[jobid].fullname
                for _, jobid in self.pending_tasks
            ]
            if running_tasks:
                tasks_list_msg = "\nCurrently running:\n"
                tasks_list_msg += "\n".join(running_tasks)
                tasks_list_msg = indent(tasks_list_msg, " " * 21)
            logger.info(
                "[MultiProc] Running %d tasks, and %d jobs ready. Free "
                "memory (GB): %0.2f/%0.2f, Free processors: %d/%d.%s, Free real memory:%s",
                len(self.pending_tasks),
                len(jobids),
                free_memory_gb,
                self.memory_gb,
                free_processors,
                self.processors,
                tasks_list_msg,
                free_real_memory_gb
            )
            self._stats = stats

        if free_memory_gb < 0.01 or free_processors == 0:
            logger.debug("No resources available")
            return

        if len(jobids) + len(self.pending_tasks) == 0:
            logger.debug(
                "No tasks are being run, and no jobs can "
                "be submitted to the queue. Potential deadlock"
            )
            return


      
        jobids = self._sort_jobs(jobids, scheduler=self.plugin_args.get("scheduler"))
        gc.collect()


        # Submit jobs
        for jobid in jobids:
            if isinstance(self.procs[jobid], MapNode):
                try:
                    num_subnodes = self.procs[jobid].num_subnodes()
                except Exception:
                    traceback = format_exception(*sys.exc_info())
                    self._clean_queue(jobid, graph, result={"result": None, "traceback": traceback})
                    self.proc_pending[jobid] = False
                    continue
                if num_subnodes > 1:
                    submit = self._submit_mapnode(jobid)
                    if not submit:
                        continue

            # Check requirements of this job
            next_job_gb = min(self.procs[jobid].mem_gb, self.memory_gb)
            next_job_th = min(self.procs[jobid].n_procs, self.processors)

            can_fit = (next_job_gb <= free_memory_gb) and (next_job_th <= free_processors)

            if not self._sequential_mode and not can_fit:
                logger.debug("Cannot allocate job %d (%0.2fGB, %d threads).", jobid, next_job_gb, next_job_th)
                continue

            free_memory_gb -= next_job_gb
            free_processors -= next_job_th
            logger.debug(
                "Allocating %s ID=%d (%0.2fGB, %d threads). Free: "
                "%0.2fGB, %d threads.",
                self.procs[jobid].fullname,
                jobid,
                next_job_gb,
                next_job_th,
                free_memory_gb,
                free_processors,
            )

            # change job status in appropriate queues
            self.proc_done[jobid] = True
            self.proc_pending[jobid] = True

            # If cached and up-to-date just retrieve it, don't run
            if self._local_hash_check(jobid, graph):
                continue

            # Run on master thread — either explicitly or due to low memory
            if updatehash or self.procs[jobid].run_without_submitting or self._sequential_mode:
                logger.debug("Running node %s on master thread (sequential=%s)", self.procs[jobid], self._sequential_mode)
                try:
                    self.procs[jobid].run(updatehash=updatehash)
                except Exception:
                    traceback = format_exception(*sys.exc_info())
                    self._clean_queue(jobid, graph, result={"result": None, "traceback": traceback})
                
                # Release resources
                self._task_finished_cb(jobid)
                self._remove_node_dirs()
                free_memory_gb += next_job_gb
                free_processors += next_job_th
                # Display stats next loop
                self._stats = None

                # Clean up any debris from running node in main process
                gc.collect()
                continue
              
            # Task should be submitted to workers
            # Send job to task manager and add to pending tasks
            if self._status_callback:
                self._status_callback(self.procs[jobid], "start")
            tid = self._submit_job(deepcopy(self.procs[jobid]), updatehash=updatehash)
            if tid is None:
                self.proc_done[jobid] = False
                self.proc_pending[jobid] = False
            else:
                self.pending_tasks.insert(0, (tid, jobid))
            # Display stats next loop
            self._stats = None


    def _submit_job(self, node, updatehash=False):
        self._taskid += 1

        # Don't allow streaming outputs
        if getattr(node.interface, "terminal_output", "") == "stream":
            node.interface.terminal_output = "allatonce"

        result_future = self.pool.submit(run_node, node, updatehash, self._taskid)
        result_future.add_done_callback(self._async_callback)
        self._task_obj[self._taskid] = result_future

        logger.debug("[MultiProc] Submitted task %s (taskid=%d).", node.fullname, self._taskid)
        return self._taskid

    def _generate_dependency_list(self, graph):
        if self._rt is not None:
            for node in graph.nodes:
                self._rt.add_node(node)
            for node in graph.nodes:
                self._rt.set_node_pending(node)
        super(MultiProcPlugin, self)._generate_dependency_list(graph)

    def _task_finished_cb(self, jobid, cached=False):
        assert self.procs is not None

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
        assert self.procs is not None

        try:
            result = args.result()
            self._taskresult[result["taskid"]] = result
        except Exception as e:
            running_tasks = [self.procs[jobid].fullname for _, jobid in self.pending_tasks]
            logger.exception(f"Exception for {args} while running {running_tasks}", exc_info=e)

    def _remove_node_dirs(self):
        """
        Removes directories whose outputs have already been used up
        """
        if self._rt is not None:
            self._rt.collect_and_delete()

