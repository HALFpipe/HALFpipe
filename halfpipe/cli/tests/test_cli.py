# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from argparse import ArgumentParser

from halfpipe import __version__


def test_cli_build_a_parser(halfpipe_parser):
    assert isinstance(halfpipe_parser, ArgumentParser)


def test_cli_parser_object_has_description(halfpipe_parser):
    assert halfpipe_parser.description


def test_cli_parser_object_description_contains_version(halfpipe_parser):
    assert __version__ in halfpipe_parser.description


def test_cli_parser_object_groups_args(halfpipe_parser):
    groups = {"base", "steps", "workflow", "run", "debug"}
    assert {group.title for group in halfpipe_parser._action_groups}.issuperset(groups)


def test_parser_can_set_workdir(halfpipe_parser):
    args = ["--workdir", "/ext/workdir"]
    opts = halfpipe_parser.parse_args(args)
    assert opts.workdir == "/ext/workdir"
