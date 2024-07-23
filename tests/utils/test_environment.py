# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import os

import pytest
from halfpipe.cli.parser import parse_args
from halfpipe.utils.environment import setup_freesurfer_env

logger = logging.getLogger()

good_opts, _ = parse_args(argv=["--fs-license-file", "/etc/hosts"])
bad_opts, _ = parse_args(argv=["--fs-license-file", "/dev/null"])


def test_freesurfer_env_works_with_env_set():
    no_opts, _ = parse_args([])

    try:
        _ = os.environ["FS_LICENSE"]
    except KeyError:
        os.environ["FS_LICENSE"] = "/dev/full"

    no_opts_test = setup_freesurfer_env(no_opts)
    assert no_opts_test is True


@pytest.mark.parametrize("opts, proper_result", [(good_opts, True), (bad_opts, False)])
def test_setup_freesurfer_env(opts, proper_result):
    try:
        del os.environ["FS_LICENSE"]
    except KeyError:
        pass

    thistest = setup_freesurfer_env(opts)
    assert thistest is proper_result
