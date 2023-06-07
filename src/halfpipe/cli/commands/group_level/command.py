# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import ArgumentParser, Namespace
from typing import Callable

from ..base import Command


class GroupLevelCommand(Command):
    def setup(self, add_parser: Callable[[str], ArgumentParser]):
        from .arguments import setup_argument_parser

        argument_parser = add_parser("group-level")
        argument_parser.set_defaults(action=self.run)
        setup_argument_parser(argument_parser)

    def run(self, arguments: Namespace):
        from .run import run

        run(arguments)
