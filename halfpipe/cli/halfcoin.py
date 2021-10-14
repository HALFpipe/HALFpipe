# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import sys
import json
import copy
from pathlib import Path
from xml.dom import ValidationErr
from marshmallow import ValidationError

from ..errors import SpecError, LicenseError
from ..logging.base import (
    setup_context as setup_logging_context,
    teardown as teardown_logging,
)
from ..model.spec import Spec, readspec
from ..utils import logger, timestampstr
from ..utils.environment import setup_freesurfer_env
from ..utils.path import validate_workdir
from .run import run_stage_run, run_stage_workflow
from .parser import parse_args


orig_stdout = sys.stdout
orig_stderr = sys.stderr


def logging_workaround(disable: bool = True) -> None:
    """
    Captures all work-around logging logic in an easy to
    remove function.  Remove this hack when we've finally
    tracked down all the places that nipype loggers are configured

    Args:
        disable: disable logging, or not.  Defaults True

    Side-Effect(s):
        sys.[stdout, stderr] become os.devnull
        orig_stdout and orig_stderr become sys.[stdout, stderr]
    sets sys.stdout and sys.stderr to os.devnull,
        and orig_stdout and orig_stderr to sys.[stdout, stderr]

    Returns:
        None
    """
    if disable:
        null = open(
            os.devnull, "w", encoding=sys.getdefaultencoding()
        )  # pylint: disable=consider-using-with
        sys.stdout = null
        sys.stderr = null
    else:
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr


def cleanup_and_exit(profile=None, pr=None, opts=None, exit_code=0):
    output_data_location = ""
    if profile and pr is not None:
        pr.disable()
        if opts is not None:
            pr.dump_stats(Path(opts.workdir) / f"profile.{timestampstr():s}.prof")
            output_data_location = opts.workdir / "derivatives"
    teardown_logging()
    # clean up orphan processes
    from ..utils.multiprocessing import terminate

    terminate()
    orig_stdout.write(
        json.dumps(
            {
                "output": {"processed_data_path": output_data_location},
                "success": exit_code,
            }
        )
    )
    sys.exit(exit_code)


def main():
    """
    Provides an interface to run halfpipe from a configuration spec provided by coinstac
    """
    if os.isatty(sys.stdin.fileno()):
        print("Please use the command halfpipe for interactive use")
        sys.exit(1)

    setup_logging_context()

    # new approach
    # create workdir automatically, in the basedirectory received from state
    # look for existing derivatives in BIDS dir, and attempt to find a roi mask?
    # create fslicense file from base64 encoded object input
    # add more files for paths to masks, rois, etc.

    # logging_workaround()

    opts = None
    pr = None
    profile = False

    # ToDo: replace all of this with a halfpipe.model.spec.CoinSpecSchema
    try:
        coinstac_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError):
        logger.error("unable to decode input")
        cleanup_and_exit(exit_code=1)

    # Create a more or less standard halfpipe spec from the coinstac inputs
    # Note: assuming we'll always get a path to a BIDS directory
    try:
        candidate_spec = copy.deepcopy(coinstac_input["input"]["halfpipespec"])
        candidate_spec["files"] = {
            "path": coinstac_input["input"]["files"],
            "datatype": "bids",
        }

        # We can accept ["input"]["args"] as a list of strings to pass to
        # argparser.  We'll set the workdir from the state dictionary though
        # if we don't get one
        candidate_args = coinstac_input["input"]["args"]
    except (KeyError, json.JSONDecodeError, AttributeError):
        logger.error("Failed to read spec from stdin; check inputs")
        cleanup_and_exit(profile, pr, opts, exit_code=1)

    try:
        _ = candidate_args.index("--workdir")
    except ValueError:
        candidate_args.extend(["--workdir", coinstac_input["state"]["outputDirectory"]])

    opts, should_run = parse_args(candidate_args)

    profile = opts.profile

    if profile is True:
        from cProfile import Profile

        pr = Profile()
        pr.enable()

    try:
        spec = readspec(candidate_spec)
    except (KeyError, json.JSONDecodeError, AttributeError):
        logger.error("Failed to read spec from stdin; check inputs")
        cleanup_and_exit(profile, pr, opts, exit_code=1)

    try:
        import nipype

        nipype.config.set("logging", "interface_level", "ERROR")
        validate_workdir(opts.workdir)

        if not setup_freesurfer_env(opts):
            logger.debug("failed to locate a valid freesurfer license")
            raise LicenseError("Failed to locate a valid freesurfer license")

        opts.graphs = None

        logger.debug(f'should_run["workflow"]={should_run["workflow"]}')
        if should_run["workflow"]:
            logger.info("Stage: workflow")
            run_stage_workflow(opts, spec)

        logger.debug(f'should_run["run"]={should_run["run"]}')
        logger.debug(f"opts.use_cluster={opts.use_cluster}")

        if should_run["run"] and not opts.use_cluster:
            logger.info("Stage: run")
            run_stage_run(opts)

    except Exception:  # pylint: disable=invalid-name,broad-except
        cleanup_and_exit(profile, pr, opts, exit_code=1)

    finally:
        cleanup_and_exit(profile, pr, opts)


if __name__ == "__main__":
    main()
