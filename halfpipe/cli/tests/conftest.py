# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pytest

from ..parser import build_parser


@pytest.fixture
def halfpipe_parser():
    return build_parser()


@pytest.fixture
def halfpipe_opts(halfpipe_parser):
    args = ["--workdir", "/ext/workdir"]
    return halfpipe_parser.parse_args(args)
