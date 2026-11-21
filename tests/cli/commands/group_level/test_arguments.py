# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from argparse import ArgumentParser

import pytest

from halfpipe.cli.commands.group_level.arguments import algorithms, setup_argument_parser


def parse_algorithm(*argv: str) -> list[str] | None:
    argument_parser = ArgumentParser()
    setup_argument_parser(argument_parser)
    arguments = argument_parser.parse_args(["--working-directory", "/tmp", *argv])
    return arguments.algorithm


def test_algorithm_defaults_to_none():
    assert parse_algorithm() is None


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["--algorithm", "flame1"], ["flame1"]),
        (["--algorithm", "flame1", "mcartest"], ["flame1", "mcartest"]),
        (["--algorithm", "flame1", "--algorithm", "descriptive"], ["flame1", "descriptive"]),
    ],
)
def test_algorithm_replaces_default(argv: list[str], expected: list[str]):
    assert parse_algorithm(*argv) == expected


def test_algorithms_lists_all_choices():
    assert set(algorithms) == {"descriptive", "flame1", "heterogeneity", "mcartest"}
