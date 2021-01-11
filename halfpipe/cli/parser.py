# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import cpu_count

from .. import __version__

steps = ["spec-ui", "workflow", "run"]


def _build_parser():
    parser = ArgumentParser(
        description=f"ENIGMA Halfpipe {__version__} is a user-friendly interface "
        "for performing reproducible analysis of fMRI data, including preprocessing, "
        "single-subject feature extraction, and group analysis."
    )

    basegroup = parser.add_argument_group("base", "")

    basegroup.add_argument(
        "--workdir", type=str, help="directory where output and intermediate files are stored",
    )
    basegroup.add_argument("--fs-root", default="/ext", help="path to the file system root")
    basegroup.add_argument("--verbose", action="store_true", default=False)

    stepgroup = parser.add_argument_group("steps", "")
    for step in steps:
        steponlygroup = stepgroup.add_mutually_exclusive_group(required=False)
        steponlygroup.add_argument(f"--only-{step}", action="store_true", default=False)
        steponlygroup.add_argument(f"--skip-{step}", action="store_true", default=False)

    workflowgroup = parser.add_argument_group("workflow", "")
    workflowgroup.add_argument("--nipype-omp-nthreads", type=int)
    workflowgroup.add_argument("--fs-license-file")

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

    rungroup = parser.add_argument_group("run", "")
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

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="print the version number and exit",
        default=False,
    )

    debuggroup = parser.add_argument_group("debug", "")
    debuggroup.add_argument("--debug", action="store_true", default=False)
    debuggroup.add_argument("--watchdog", action="store_true", default=False)

    return parser


def parse_args(args=None, namespace=None):
    parser = _build_parser()
    opts = parser.parse_args(args, namespace)

    if opts.version is True:
        import sys

        print(__version__)
        sys.exit(0)

    from ..logging import Context as LoggingContext

    LoggingContext.enablePrint()

    debug = opts.debug
    if debug:
        import logging
        from ..logging import setup as setuplogging

        setuplogging(LoggingContext.queue(), levelno=logging.DEBUG)

    if opts.watchdog is True:
        from ..watchdog import init_watchdog

        init_watchdog()

    from fmriprep import config

    config.execution.debug = ["all"] if debug else []

    verbose = opts.verbose
    if verbose:
        LoggingContext.enableVerbose()

    should_run = {step: True for step in steps}

    for step in steps:
        attrname = f"only-{step}".replace("-", "_")
        if getattr(opts, attrname) is True:
            should_run = {step0: step0 == step for step0 in steps}
            break

    for step in steps:
        attrname = f"skip-{step}".replace("-", "_")
        if getattr(opts, attrname) is True:
            should_run[step] = False

    workdir = opts.workdir
    if workdir is not None:  # resolve workdir in fs_root
        from os.path import normpath

        abspath = str(Path(workdir).resolve())
        if not abspath.startswith(opts.fs_root):
            abspath = normpath(opts.fs_root + abspath)
        workdir = abspath

        LoggingContext.setWorkdir(workdir)
    opts.workdir = workdir

    return opts, should_run
