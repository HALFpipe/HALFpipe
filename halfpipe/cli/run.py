# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os

from pprint import pformat
from pathlib import Path

from ..utils import first, logger


def run(opts, should_run):
    # print info

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

    if opts.fs_license_file and Path(opts.fs_license_file).is_file():
        os.environ["FS_LICENSE"] = str(opts.fs_license_file)
    else:
        from glob import glob

        license_files = list(glob(str(
            Path(workdir) / "*license*"
        )))

        if len(license_files) > 0:
            license_file = str(first(license_files))
            os.environ["FS_LICENSE"] = license_file

    if os.environ.get("FS_LICENSE") is not None:
        logger.debug(f'Using FreeSurfer license "{os.environ["FS_LICENSE"]}"')

    execgraphs = None

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

        from ..workflow import init_workflow, init_execgraph

        workflow = init_workflow(workdir)

        if workflow is None:
            return

        execgraphs = init_execgraph(
            workdir,
            workflow,
            n_chunks=opts.n_chunks,
            subject_chunks=opts.subject_chunks or opts.use_cluster
        )

        if execgraphs is None:
            return

        if opts.use_cluster:
            from ..cluster import create_example_script

            create_example_script(workdir, execgraphs)

    logger.debug(f'should_run["run"]={should_run["run"]}')
    logger.debug(f"opts.use_cluster={opts.use_cluster}")

    if should_run["run"] and not opts.use_cluster:
        logger.info("Stage: run")

        if execgraphs is None:
            from ..io import loadpicklelzma

            assert (
                opts.execgraph_file is not None
            ), "Missing required --execgraph-file input for step run"
            execgraphs = loadpicklelzma(opts.execgraph_file)
            if not isinstance(execgraphs, list):
                execgraphs = [execgraphs]
            logger.info(f'Using execgraphs defined in file "{opts.execgraph_file}"')
        else:
            logger.info("Using execgraphs from previous step")

        if opts.nipype_resource_monitor is True:
            from nipype import config as nipypeconfig
            nipypeconfig.enable_resource_monitor()

        import nipype.pipeline.plugins as nip
        import halfpipe.plugins as ppp

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

        if hasattr(ppp, runnername):
            logger.info(f'Using a patched version of nipype_run_plugin "{runnername}"')
            runnercls = getattr(ppp, runnername)

        elif hasattr(nip, runnername):
            logger.warning(f'Using unsupported nipype_run_plugin "{runnername}"')
            runnercls = getattr(nip, runnername)

        else:
            raise ValueError(f'Unknown nipype_run_plugin "{runnername}"')

        logger.debug(f'Using plugin arguments\n{pformat(plugin_args)}')

        execgraphstorun = []

        if len(execgraphs) > 1:
            n_subjectlevel_chunks = len(execgraphs) - 1
            if opts.only_model_chunk:
                logger.info("Will not run subject level chunks")
                logger.info("Will run model chunk")
                execgraphstorun.append(execgraphs[-1])

            elif opts.only_chunk_index is not None:
                zerobasedchunkindex = opts.only_chunk_index - 1
                assert zerobasedchunkindex < n_subjectlevel_chunks
                logger.info(
                    f"Will run subject level chunk {opts.only_chunk_index} of {n_subjectlevel_chunks}"
                )
                logger.info("Will not run model chunk")
                execgraphstorun.append(execgraphs[zerobasedchunkindex])

            else:
                logger.info(f"Will run all {n_subjectlevel_chunks} subject level chunks")
                logger.info("Will run model chunk")
                execgraphstorun.extend(execgraphs)

        elif len(execgraphs) == 1:
            execgraphstorun.append(execgraphs[0])

        else:
            raise ValueError("No execgraphs")

        n_execgraphstorun = len(execgraphstorun)
        for i, execgraph in enumerate(execgraphstorun):
            if len(execgraphs) > 1:
                logger.info(f"Running chunk {i+1} of {n_execgraphstorun}")

            try:
                runner = runnercls(plugin_args=plugin_args)
                firstnode = first(execgraph.nodes())
                if firstnode is not None:
                    runner.run(execgraph, updatehash=False, config=firstnode.config)
            except Exception as e:
                if opts.debug:
                    raise e
                else:
                    logger.warning(f"Ignoring exception in chunk {i+1}", exc_info=True)

            if len(execgraphs) > 1:
                logger.info(f"Completed chunk {i+1} of {n_execgraphstorun}")


def main():
    from ..logging import (
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
