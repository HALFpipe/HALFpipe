# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import sys

os.environ["NIPYPE_NO_ET"] = "1"  # noqa; disable nipype update check
os.environ["NIPYPE_NO_MATLAB"] = "1"  # noqa

from os import path as op
from multiprocessing import set_start_method

set_start_method("forkserver", force=True)

global debug
debug = False


def _main():
    from . import __version__
    from argparse import ArgumentParser

    ap = ArgumentParser(
        description="mindandbrain/pipeline is a user-friendly interface "
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
    basegroup.add_argument(
        "--fs-root", default="/ext", help="directory where input files are stored"
    )
    basegroup.add_argument("--debug", action="store_true", default=False)

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
        "--n-chunks", type=int, help="number of subjectlevel chunks to generate"
    )

    rungroup = ap.add_argument_group("run", "")

    rungroup.add_argument("--execgraph-file", type=str, help="manually select file to run")

    rungroup.add_argument(
        "--chunk-index", type=int, help="select which subjectlevel chunk to run"
    )

    rungroup.add_argument("--max-mem-gb", type=float)
    rungroup.add_argument("--max-n-cores", type=int)
    rungroup.add_argument("--nipype-run-plugin", type=str, default="MultiProc")

    ap.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="print the version number and exit",
        default=False,
    )

    args = ap.parse_args()
    global debug
    debug = args.debug

    if args.version is True:
        sys.stdout.write(f"{__version__}\n")
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

    workdir = args.workdir

    if should_run["spec-ui"]:
        from .ui import init_spec_ui

        workdir = init_spec_ui(args.fs_root, workdir=workdir)

    assert workdir is not None, "Missing working directory"
    assert op.isdir(workdir), "Working directory does not exist"

    import logging
    from .logger import Logger

    if not Logger.is_setup:
        Logger.setup(workdir, debug=debug)
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

        execgraphs = init_execgraph(workdir, workflow, n_chunks=args.n_chunks)

    if not should_run["run"]:
        logger.info(f"Did not run step: run-subjectlevel")
    else:
        from nipype.pipeline import plugins

        runner = getattr(plugins, f"{args.nipype_run_plugin}Plugin")()
        # import pdb
        #
        # pdb.set_trace()
        # if not should_run["run-subjectlevel"]:
        #     logger.info(f"Did not run step: run-subjectlevel")
        # else:
        #     if args.chunk_index is not None:
        #         runner.run(execgraph, updatehash=False, config=workflow.config)
        #
        # if not should_run["run-grouplevel"]:
        #     logger.info(f"Did not run step: run-grouplevel")
        # else:
        #     pass
        # else:
        for execgraph in execgraphs:
            runner.run(execgraph, updatehash=False, config=workflow.config)


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
