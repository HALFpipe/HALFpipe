# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import sys

os.environ["NIPYPE_NO_ET"] = "1"  # noqa; disable nipype update check
os.environ["NIPYPE_NO_MATLAB"] = "1"  # noqa

from os import path as op

global debug
debug = False


def _main():
    from . import __version__
    from argparse import ArgumentParser

    ap = ArgumentParser(
        description=f"mindandbrain/pipeline {__version__} is a user-friendly interface "
        "for performing reproducible analysis of fMRI data, including preprocessing, "
        "single-subject feature extraction, and group analysis."
    )

    basegroup = ap.add_argument_group("base", "")

    basegroup.add_argument(
        "-w",
        "--workdir",
        type=str,
        help="directory where output and intermediate files are stored",
    )
    basegroup.add_argument("--fs-root", default="/ext", help="path to the file system root")
    basegroup.add_argument("--debug", action="store_true", default=False)
    basegroup.add_argument("--verbose", action="store_true", default=False)

    stepgroup = ap.add_argument_group("steps", "")
    steponlygroup = stepgroup.add_mutually_exclusive_group(required=False)
    steps = ["spec-ui", "workflow", "execgraph", "run", "run-subjectlevel", "run-grouplevel"]
    for step in steps:
        steponlygroup.add_argument(f"--{step}-only", action="store_true", default=False)
        steponlygroup.add_argument(f"--skip-{step}", action="store_true", default=False)
        if "run" not in step:
            stepgroup.add_argument(f"--stop-after-{step}", action="store_true", default=False)

    execgraphgroup = ap.add_argument_group("execgraph", "")
    execgraphgroup.add_argument(
        "--workflow-file", type=str, help="manually select workflow file"
    )
    chunkinggroup = execgraphgroup.add_mutually_exclusive_group(required=False)
    chunkinggroup.add_argument(
        "--n-chunks", type=int, help="number of subject-level workflow chunks to generate"
    )
    chunkinggroup.add_argument(
        "--subject-chunks",
        action="store_true",
        default=False,
        help="generate one subject-level workflow per subject",
    )

    rungroup = ap.add_argument_group("run", "")
    rungroup.add_argument(
        "--execgraphs-file", type=str, help="manually select execgraphs file"
    )
    rungroup.add_argument(
        "--chunk-index", type=int, help="select which subjectlevel chunk to run"
    )
    rungroup.add_argument("--nipype-memory-gb", type=float)
    rungroup.add_argument("--nipype-n-procs", type=int)
    rungroup.add_argument("--nipype-run-plugin", type=str, default="MultiProc")

    ap.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="print the version number and exit",
        default=False,
    )
    ap.add_argument(
        "--preproc-report", action="store_true", help="print a report", default=False,
    )

    args = ap.parse_args()
    global debug
    debug = args.debug
    verbose = args.verbose

    if args.version is True:
        sys.stdout.write(f"{__version__}\n")
        sys.exit(0)

    if args.preproc_report is True:
        # TODO
        sys.exit(0)

    should_run = {step: True for step in steps}

    for step in steps:
        attrname = f"{step}-only".replace("-", "_")
        if getattr(args, attrname) is True:
            should_run = {step0: step0 == step for step0 in steps}
            break

    for step in steps:
        if "run" in step:
            continue
        attrname = f"stop-after-{step}".replace("-", "_")
        if getattr(args, attrname) is True:
            state = True
            for step0 in steps:
                should_run[step0] = state
                if step0 == step:
                    state = False
            break

    for step in steps:
        attrname = f"skip-{step}".replace("-", "_")
        if getattr(args, attrname) is True:
            should_run[step] = False

    from calamities.config import config as calamities_config

    calamities_config.fs_root = args.fs_root
    from calamities.file import resolve

    workdir = args.workdir
    if workdir is not None:
        workdir = resolve(workdir)

    if should_run["spec-ui"]:
        from .ui import init_spec_ui

        workdir = init_spec_ui(workdir=workdir, debug=debug)

    assert workdir is not None, "Missing working directory"
    assert op.isdir(workdir), "Working directory does not exist"

    import logging
    from .logger import Logger

    if not Logger.is_setup:
        Logger.setup(workdir, debug=debug, verbose=verbose)
    logger = logging.getLogger("pipeline")

    logger.info(f"Version: {__version__}")
    logger.info(f"Debug: {debug}")

    if not should_run["spec-ui"]:
        logger.info(f"Did not run step: spec")

    workflow = None

    if not should_run["workflow"]:
        logger.info(f"Did not run step: workflow")
    else:
        logger.info(f"Running step: workflow")
        from .workflow import init_workflow

        workflow = init_workflow(workdir)

    execgraphs = None

    if not should_run["execgraph"]:
        logger.info(f"Did not run step: execgraph")
    else:
        logger.info(f"Running step: execgraph")
        from .execgraph import init_execgraph

        if workflow is None:
            from .utils import loadpicklelzma

            assert (
                args.workflow_file is not None
            ), "Missing required --workflow-file input for step execgraph"
            workflow = loadpicklelzma(args.workflow_file)
            logger.info(f'Using workflow defined in file "{args.workflow_file}"')
        else:
            logger.info(f"Using workflow from previous step")

        execgraphs = init_execgraph(
            workdir, workflow, n_chunks=args.n_chunks, subject_chunks=args.subject_chunks
        )

    if not should_run["run"]:
        logger.info(f"Did not run step: run")
    else:
        logger.info(f"Running step: run")
        if execgraphs is None:
            from .utils import loadpicklelzma

            assert (
                args.execgraphs_file is not None
            ), "Missing required --execgraph-file input for step run"
            execgraphs = loadpicklelzma(args.execgraphs_file)
            if not isinstance(execgraphs, list):
                execgraphs = [execgraphs]
            logger.info(f'Using execgraphs defined in file "{args.execgraphs_file}"')
        else:
            logger.info(f"Using execgraphs from previous step")

        from nipype.pipeline import plugins as nip
        from pipeline import plugins as ppp

        plugin_args = {"workdir": workdir, "debug": debug, "verbose": verbose}
        if args.nipype_n_procs is not None:
            plugin_args["n_procs"] = args.nipype_n_procs
        if args.nipype_memory_gb is not None:
            plugin_args["memory_gb"] = args.nipype_memory_gb

        runnername = f"{args.nipype_run_plugin}Plugin"
        if hasattr(ppp, runnername):
            logger.info(f'Using a patched version of nipype_run_plugin "{runnername}"')
            runnercls = getattr(ppp, runnername)
        elif hasattr(nip, runnername):
            logger.info(f'Using nipype_run_plugin "{runnername}"')
            runnercls = getattr(nip, runnername)
        else:
            raise ValueError(f'Unknown nipype_run_plugin "{runnername}"')
        runner = runnercls(plugin_args=plugin_args)

        execgraphstorun = []
        if len(execgraphs) > 1:
            n_subjectlevel_chunks = len(execgraphs) - 1
            if not should_run["run-subjectlevel"]:
                logger.info(f"Will not run subjectlevel chunks")
            elif args.chunk_index is not None:
                zerobasedchunkindex = args.chunk_index - 1
                assert zerobasedchunkindex < n_subjectlevel_chunks
                logger.info(
                    f"Will run subjectlevel chunk {args.chunk_index} of {n_subjectlevel_chunks}"
                )
                execgraphstorun.append(execgraphs[zerobasedchunkindex])
            else:
                logger.info(f"Will run all {n_subjectlevel_chunks} subjectlevel chunks")
                execgraphstorun.extend(execgraphs[:-1])

            if not should_run["run-grouplevel"]:
                logger.info(f"Will not run grouplevel chunk")
            else:
                logger.info(f"Will run grouplevel chunk")
                execgraphstorun.append(execgraphs[-1])
        elif len(execgraphs) == 1:
            execgraphstorun.append(execgraphs[0])
        else:
            raise ValueError("No execgraphs")

        n_execgraphstorun = len(execgraphstorun)
        for i, execgraph in enumerate(execgraphstorun):
            if len(execgraphs) > 1:
                logger.info(f"Running chunk {i+1} of {n_execgraphstorun}")
            runner.run(execgraph, updatehash=False, config=workflow.config)
            if len(execgraphs) > 1:
                logger.info(f"Completed chunk {i+1} of {n_execgraphstorun}")


def main():
    try:
        _main()
    except Exception as e:
        import logging

        logger = logging.getLogger("pipeline")
        logger.exception("Exception: %s", e)

        global debug
        if debug:
            import pdb

            pdb.post_mortem()
