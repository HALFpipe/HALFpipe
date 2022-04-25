# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import os
import pytest


from ...cli.parser import parse_args
from ..environment import setup_freesurfer_env


logger = logging.getLogger()

good_opts, _ = parse_args(["--fs-license-file", "./README.rst"])
bad_opts, _ = parse_args(["--fs-license-file", "/dev/null"])


@pytest.mark.parametrize("opts, proper_result", [(good_opts, True), (bad_opts, False)])
def test_setup_freesurfer_env(opts, proper_result):

    try:
        del os.environ["FS_LICENSE"]
    except KeyError:
        pass

    thistest = setup_freesurfer_env(opts)
    assert thistest == proper_result
