# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
import sys
import logging

from . import __version__

from fmriprep import config

global debug
debug = False


def _main():
    from argparse import ArgumentParser
    from multiprocessing import cpu_count
    from pprint import pformat

    ap = ArgumentParser(
        description=f"ENIGMA Halfpipe {__version__} is a user-friendly interface "
        "for performing reproducible analysis of fMRI data, including preprocessing, "
        "single-subject feature extraction, and group analysis."
    )

    basegroup = ap.add_argument_group("base", "")

    basegroup.add_argument(
        "--workdir", type=str, help="directory where output and intermediate files are stored",
    )
    basegroup.add_argument("--fs-root", default="/ext", help="path to the file system root")
    basegroup.add_argument("--verbose", action="store_true", default=False)

    stepgroup = ap.add_argument_group("steps", "")
    steps = ["spec-ui", "workflow", "run"]
    for step in steps:
        steponlygroup = stepgroup.add_mutually_exclusive_group(required=False)
        steponlygroup.add_argument(f"--only-{step}", action="store_true", default=False)
        steponlygroup.add_argument(f"--skip-{step}", action="store_true", default=False)

    workflowgroup = ap.add_argument_group("workflow", "")
    workflowgroup.add_argument("--nipype-omp-nthreads", type=int)
    chunkinggroup = workflowgroup.add_mutually_exclusive_group(required=False)
    chunkinggroup.add_argument(
        "--n-chunks", type=int, help="number of subject-level workflow chunks to generate"
    )
    chunkinggroup.add_argument(
        "--subject-chunks",
        action="store_true",
        default=False,
        help="generate one subject-level workflow per subject",
    )
    chunkinggroup.add_argument(
        "--use-cluster",
        action="store_true",
        default=False,
        help="generate workflow suitable for running on a cluster",
    )

    rungroup = ap.add_argument_group("run", "")
    rungroup.add_argument("--execgraph-file", type=str, help="manually select execgraph file")
    rungroup.add_argument("--only-chunk-index", type=int, help="select which chunk to run")
    rungroup.add_argument("--only-model-chunk", action="store_true", default=False)
    rungroup.add_argument("--nipype-memory-gb", type=float)
    rungroup.add_argument("--nipype-n-procs", type=int, default=cpu_count())
    rungroup.add_argument("--nipype-run-plugin", type=str, default="MultiProc")
    rungroup.add_argument("--nipype-resource-monitor", action="store_true", default=False)
    rungroup.add_argument(
        "--keep",
        choices=["all", "some", "none"],
        default="some",
        help="choose which intermediate files to keep",
    )

    ap.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="print the version number and exit",
        default=False,
    )

    debuggroup = ap.add_argument_group("debug", "")
    debuggroup.add_argument("--debug", action="store_true", default=False)
    debuggroup.add_argument("--watchdog", action="store_true", default=False)

    args = ap.parse_args()
    global debug
    debug = args.debug
    config.execution.debug = ["all"] if debug else []
    verbose = args.verbose

    if args.version is True:
        sys.stdout.write(f"{__version__}\n")
        sys.exit(0)

    should_run = {step: True for step in steps}

    for step in steps:
        attrname = f"only-{step}".replace("-", "_")
        if getattr(args, attrname) is True:
            should_run = {step0: step0 == step for step0 in steps}
            break

    for step in steps:
        attrname = f"skip-{step}".replace("-", "_")
        if getattr(args, attrname) is True:
            should_run[step] = False

    workdir = args.workdir
    if workdir is not None:  # resolve workdir in fs_root
        from os.path import normpath

        abspath = str(Path(workdir).resolve())
        if not abspath.startswith(args.fs_root):
            abspath = normpath(args.fs_root + abspath)
        workdir = abspath

    if should_run["spec-ui"]:
        from .ui import init_spec_ui
        from calamities.config import config as calamities_config

        calamities_config.fs_root = args.fs_root
        workdir = init_spec_ui(workdir=workdir, debug=debug)

    assert workdir is not None, "Missing working directory"
    assert Path(workdir).is_dir(), "Working directory does not exist"

    import logging
    from .logger import Logger

    Logger.setup(workdir, debug=debug, verbose=verbose)
    logger = logging.getLogger("halfpipe")

    if not verbose and not debug:
        logger.log(
            25,
            'Option "--verbose" was not specified. Will not print detailed logs to the terminal. \n'
            'Detailed logs information will only be available in the "log.txt" file in the working directory. '
        )

    logger.info(f"Version: {__version__}")
    logger.info(f"Debug: {debug}")

    if args.watchdog is True:
        from .watchdog import start_watchdog_daemon

        start_watchdog_daemon()

    if not should_run["spec-ui"]:
        logger.info("Did not run step: spec")

    execgraphs = None

    if not should_run["workflow"]:
        logger.info("Did not run step: workflow")
    else:
        logger.info("Running step: workflow")
        from .workflow import init_workflow, init_execgraph

        if args.nipype_omp_nthreads is not None and args.nipype_omp_nthreads > 0:
            config.nipype.omp_nthreads = args.nipype_omp_nthreads
            logger.info(f"Using config.nipype.omp_nthreads={config.nipype.omp_nthreads} from args")
        elif args.use_cluster:
            config.nipype.omp_nthreads = 2
        else:
            config.nipype.omp_nthreads = (
                8 if args.nipype_n_procs > 16 else (4 if args.nipype_n_procs > 8 else 1)
            )
            logger.info(f"Inferred config.nipype.omp_nthreads={config.nipype.omp_nthreads}")
        workflow = init_workflow(workdir)
        Logger.setup(workdir, debug=debug, verbose=verbose)  # re-run setup to override fmriprep/nipype logging config
        execgraphs = init_execgraph(
            workdir,
            workflow,
            n_chunks=args.n_chunks,
            subject_chunks=args.subject_chunks or args.use_cluster
        )
        if args.use_cluster:
            from .cluster import create_example_script

            create_example_script(workdir, execgraphs)

    if not should_run["run"] or args.use_cluster:
        logger.info("Did not run step: run")
    else:
        logger.info("Running step: run")
        if execgraphs is None:
            from .io import loadpicklelzma

            assert (
                args.execgraph_file is not None
            ), "Missing required --execgraph-file input for step run"
            execgraphs = loadpicklelzma(args.execgraph_file)
            if not isinstance(execgraphs, list):
                execgraphs = [execgraphs]
            logger.info(f'Using execgraphs defined in file "{args.execgraph_file}"')
        else:
            logger.info("Using execgraphs from previous step")

        if args.nipype_resource_monitor is True:
            from nipype import config as nipypeconfig
            nipypeconfig.enable_resource_monitor()

        import nipype.pipeline.plugins as nip
        import halfpipe.plugins as ppp

        plugin_args = {
            "workdir": workdir,
            "debug": debug,
            "verbose": verbose,
            "watchdog": args.watchdog,
            "stop_on_first_crash": debug,
            "raise_insufficient": False,
            "keep": args.keep,
        }
        if args.nipype_n_procs is not None:
            plugin_args["n_procs"] = args.nipype_n_procs
        if args.nipype_memory_gb is not None:
            plugin_args["memory_gb"] = args.nipype_memory_gb
        else:
            from .memory import memorylimit

            memory_gb = memorylimit()
            if memory_gb is not None:
                plugin_args["memory_gb"] = memory_gb

        runnername = f"{args.nipype_run_plugin}Plugin"
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
            if args.only_model_chunk:
                logger.info("Will not run subject level chunks")
                logger.info("Will run model chunk")
                execgraphstorun.append(execgraphs[-1])
            elif args.only_chunk_index is not None:
                zerobasedchunkindex = args.only_chunk_index - 1
                assert zerobasedchunkindex < n_subjectlevel_chunks
                logger.info(
                    f"Will run subject level chunk {args.only_chunk_index} of {n_subjectlevel_chunks}"
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
            from .utils import first

            if len(execgraphs) > 1:
                logger.info(f"Running chunk {i+1} of {n_execgraphstorun}")
            try:
                runner = runnercls(plugin_args=plugin_args)
                firstnode = first(execgraph.nodes())
                if firstnode is not None:
                    runner.run(execgraph, updatehash=False, config=firstnode.config)
            except Exception as e:
                logger.warning(f"Ignoring exception in chunk {i+1}: %s", e)
            if len(execgraphs) > 1:
                logger.info(f"Completed chunk {i+1} of {n_execgraphstorun}")


def main():
    try:
        _main()
    except Exception as e:
        logger = logging.getLogger("halfpipe")
        logger.exception("Exception: %s", e)

        global debug
        if debug:
            import pdb

            pdb.post_mortem()
