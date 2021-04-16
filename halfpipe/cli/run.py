# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict

import os
from pprint import pformat
from pathlib import Path
from itertools import islice

from glob import glob
from math import ceil

import numpy as np
import networkx as nx

from ..utils import first, logger, resolve


def run(opts, should_run):
    # log some basic information
    from .. import __version__

    logger.info(f"HALFpipe version {__version__}")

    if not opts.verbose:
        logger.log(
            25,
            'Option "--verbose" was not specified. Will not print detailed logs to the terminal. \n'
            'Detailed logs information will only be available in the "log.txt" file in the working directory. '
        )

    logger.debug(f"debug={opts.debug}")

    workdir = opts.workdir
    if workdir is not None:
        workdir = Path(workdir)
        workdir.mkdir(exist_ok=True, parents=True)

    logger.debug(f'should_run["spec-ui"]={should_run["spec-ui"]}')
    if should_run["spec-ui"]:
        logger.info("Stage: spec-ui")

        from ..ui import init_spec_ui
        from calamities.config import Config as CalamitiesConfig

        CalamitiesConfig.fs_root = opts.fs_root
        workdir = init_spec_ui(workdir=workdir, debug=opts.debug)

    assert workdir is not None, "Missing working directory"
    assert Path(workdir).is_dir(), "Working directory does not exist"

    if opts.fs_license_file is not None:
        fs_license_file = resolve(opts.fs_license_file, opts.fs_root)
        if fs_license_file.is_file():
            os.environ["FS_LICENSE"] = str(fs_license_file)
    else:
        license_files = list(glob(str(
            Path(workdir) / "*license*"
        )))

        if len(license_files) > 0:
            license_file = str(first(license_files))
            os.environ["FS_LICENSE"] = license_file

    if os.environ.get("FS_LICENSE") is not None:
        logger.debug(f'Using FreeSurfer license "{os.environ["FS_LICENSE"]}"')

    graphs = None

    logger.debug(f'should_run["workflow"]={should_run["workflow"]}')
    if should_run["workflow"]:
        logger.info("Stage: workflow")

        from fmriprep import config

        if opts.nipype_omp_nthreads is not None and opts.nipype_omp_nthreads > 0:
            config.nipype.omp_nthreads = opts.nipype_omp_nthreads
            omp_nthreads_origin = "command line arguments"

        elif opts.use_cluster:
            config.nipype.omp_nthreads = 2
            omp_nthreads_origin = "from --use-cluster"

        else:
            omp_nthreads = opts.nipype_n_procs // 4
            if omp_nthreads < 1:
                omp_nthreads = 1
            if omp_nthreads > 8:
                omp_nthreads = 8
            config.nipype.omp_nthreads = omp_nthreads

            omp_nthreads_origin = "inferred"

        logger.info(f"config.nipype.omp_nthreads={config.nipype.omp_nthreads} ({omp_nthreads_origin})")

        from ..workflow.base import init_workflow
        from ..workflow.execgraph import init_execgraph

        workflow = init_workflow(workdir)

        if workflow is None:
            return

        graphs = init_execgraph(workdir, workflow)

        if graphs is None:
            return

        if opts.use_cluster:
            from ..cluster import create_example_script

            create_example_script(workdir, graphs, opts)

    logger.debug(f'should_run["run"]={should_run["run"]}')
    logger.debug(f"opts.use_cluster={opts.use_cluster}")

    if should_run["run"] and not opts.use_cluster:
        logger.info("Stage: run")

        if graphs is None:
            from ..io import loadpicklelzma

            assert (
                opts.graphs_file is not None
            ), "Missing required --graphs-file input for step run"
            graphs = loadpicklelzma(opts.graphs_file)
            assert isinstance(graphs, OrderedDict)
            logger.info(f'Using graphs defined in file "{opts.graphs_file}"')
        else:
            logger.info("Using graphs from previous step")

        if opts.nipype_resource_monitor is True:
            from nipype import config as nipypeconfig
            nipypeconfig.enable_resource_monitor()

        plugin_args = {
            "workdir": workdir,
            "watchdog": opts.watchdog,
            "stop_on_first_crash": opts.debug,
            "raise_insufficient": False,
            "keep": opts.keep,
        }

        if opts.nipype_n_procs is not None:
            plugin_args["n_procs"] = opts.nipype_n_procs

        if opts.nipype_memory_gb is not None:
            plugin_args["memory_gb"] = opts.nipype_memory_gb
        else:
            from ..memory import memorylimit

            memory_gb = memorylimit()
            if memory_gb is not None:
                plugin_args["memory_gb"] = memory_gb

        runnername = f"{opts.nipype_run_plugin}Plugin"

        import nipype.pipeline.plugins as nip
        import halfpipe.plugins as ppp

        if hasattr(ppp, runnername):
            logger.info(f'Using a patched version of nipype_run_plugin "{runnername}"')
            runnercls = getattr(ppp, runnername)

        elif hasattr(nip, runnername):
            logger.warning(f'Using unsupported nipype_run_plugin "{runnername}"')
            runnercls = getattr(nip, runnername)

        else:
            raise ValueError(f'Unknown nipype_run_plugin "{runnername}"')

        logger.debug(f'Using plugin arguments\n{pformat(plugin_args)}')

        reversed_graph_items_iter = iter(reversed(graphs.items()))
        last_graph_name, model_chunk = next(reversed_graph_items_iter)
        assert last_graph_name == "model", "Last graph needs to be model chunk"

        from ..workflow.execgraph import filter_subject_graphs

        subject_graphs = OrderedDict([*reversed_graph_items_iter])
        subject_graphs = filter_subject_graphs(subject_graphs, opts)

        n_chunks = opts.n_chunks
        if n_chunks is None:
            if opts.subject_chunks or opts.use_cluster:
                n_chunks = len(subject_graphs)
            else:
                n_chunks = ceil(len(subject_graphs) / float(opts.max_chunk_size))

        subjectlevel_chunks = []
        graphs_iter = iter(subject_graphs.values())

        index_arrays = np.array_split(np.arange(len(subject_graphs)), n_chunks)
        for index_array in index_arrays:
            graph_list = list(islice(graphs_iter, len(index_array)))
            subjectlevel_chunks.append(
                nx.compose_all(graph_list)
            )  # take len(index_array) subjects and compose

        chunks_to_run = list()

        if opts.only_chunk_index is not None:
            zero_based_chunk_index = opts.only_chunk_index - 1
            if zero_based_chunk_index >= n_chunks or zero_based_chunk_index < 0:
                logger.info(f"Not running chunk {opts.only_chunk_index} as is not defined")
                return

            logger.info(
                f"Will run subject level chunk {opts.only_chunk_index} of {n_chunks}"
            )
            logger.info("Will not run model chunk")

            chunks_to_run.append(
                subjectlevel_chunks[zero_based_chunk_index]
            )

        elif opts.only_model_chunk:
            logger.info("Will not run subject level chunks")
            logger.info("Will run model chunk")

            chunks_to_run.append(model_chunk)

        elif len(subjectlevel_chunks) > 0:
            if len(subjectlevel_chunks) > 1:
                logger.info(f"Will run all {n_chunks} subject level chunks")
            else:
                logger.info("Will run the subject level chunk")
            logger.info("Will run model chunk")

            chunks_to_run.extend(subjectlevel_chunks)
            chunks_to_run.append(model_chunk)

        else:
            raise ValueError("No graphs to run")

        from nipype.pipeline import engine as pe

        for i, chunk in enumerate(chunks_to_run):
            if len(chunks_to_run) > 1:
                logger.info(f"Running chunk {i+1} of {len(chunks_to_run)}")

            try:
                assert isinstance(chunk, nx.DiGraph)

                runner = runnercls(plugin_args=plugin_args)
                firstnode = first(chunk.nodes())
                assert isinstance(firstnode, pe.Node)
                if firstnode is not None:
                    runner.run(chunk, updatehash=False, config=firstnode.config)
            except Exception as e:
                if opts.debug:
                    raise e
                else:
                    logger.warning(f"Ignoring exception in chunk {i+1}", exc_info=True)

            if len(chunks_to_run) > 1:
                logger.info(f"Completed chunk {i+1} of {len(chunks_to_run)}")


def main():
    from ..logging.base import (
        setupcontext as setuplogging,
        teardown as teardownlogging
    )

    debug = False

    try:
        setuplogging()

        from .parser import parse_args
        opts, should_run = parse_args()

        debug = opts.debug

        run(opts, should_run)
    except Exception as e:
        logger.exception("Exception: %s", e, exc_info=True)

        if debug:
            import pdb

            pdb.post_mortem()
    finally:
        teardownlogging()

        # clean up orphan processes

        from multiprocessing import get_context

        ctx = get_context("forkserver")
        for p in ctx.active_children():
            p.terminate()
