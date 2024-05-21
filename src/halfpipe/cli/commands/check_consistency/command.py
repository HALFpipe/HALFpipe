# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Callable

from ..base import Command


class CheckConsistencyCommand(Command):
    def setup(self, add_parser: Callable[[str], ArgumentParser]):
        argument_parser = add_parser("check-consistency")
        argument_parser.set_defaults(action=self.run)

        argument_parser.add_argument(
            "--output-directory",
            "--outdir",
            type=str,
            required=True,
            help="the directory to write the results to",
        )

    def run(self, arguments: Namespace):
        output_directory: Path = Path(arguments.output_directory)
        print(output_directory)
        import pdb

        pdb.set_trace()
