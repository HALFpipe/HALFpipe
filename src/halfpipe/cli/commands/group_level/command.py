# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import ArgumentParser, Namespace
from typing import Callable

from ..base import Command


class GroupLevelCommand(Command):
    def setup(self, add_parser: Callable[[str], ArgumentParser]):
        argument_parser = add_parser("group-level")
        argument_parser.set_defaults(action=self.run)

        argument_parser.add_argument(
            "--input-directory",
            "--working-directory",
            "--workdir",
            "--wd",
            type=str,
            nargs="+",
            action="extend",
            required=True,
        )
        argument_parser.add_argument(
            "--output-directory",
            "--outdir",
            type=str,
            required=False,
            dest="workdir",
        )

        argument_parser.add_argument(
            "--from-spec",
            default=False,
            action="store_true",
        )

        argument_parser.add_argument(
            "--model-name",
            type=str,
        )

        argument_parser.add_argument(
            "--rename",
            type=str,
            nargs=3,
            metavar=("TAG", "FROM", "TO"),
            action="append",
        )

        argument_parser.add_argument(
            "--include",
            type=str,
            nargs=2,
            metavar=("TAG", "VALUE"),
            action="append",
        )
        argument_parser.add_argument(
            "--exclude",
            type=str,
            nargs=2,
            metavar=("TAG", "VALUE"),
            action="append",
        )

        argument_parser.add_argument(
            "--qc-exclude-files",
            type=str,
            nargs="+",
            action="extend",
        )

        argument_parser.add_argument(
            "--spreadsheet",
            type=str,
            required=False,
        )
        argument_parser.add_argument(
            "--id-column",
            type=str,
            required=False,
        )
        argument_parser.add_argument(
            "--categorical-variable",
            type=str,
            action="append",
        )
        argument_parser.add_argument(
            "--levels",
            type=str,
            nargs="+",
            action="append",
        )
        argument_parser.add_argument(
            "--continuous-variable",
            type=str,
            action="append",
        )

        argument_parser.add_argument(
            "--fd-mean-cutoff",
            type=float,
            default=0.5,
        )
        argument_parser.add_argument(
            "--fd-perc-cutoff",
            type=float,
            default=10,
        )
        argument_parser.add_argument(
            "--missing-value-strategy",
            choices=("listwise-deletion",),
            default="listwise-deletion",
        )
        argument_parser.add_argument(
            "--algorithm",
            type=str,
            nargs="+",
            action="extend",
        )
        argument_parser.add_argument(
            "--aggregate",
            type=str,
            metavar="across",
            nargs="+",
            action="extend",
        )

        argument_parser.add_argument(
            "--export",
            type=str,
            nargs=4,
            metavar=("NAME", "TYPE", "IMAGE_PATH", "LABEL_PATH"),
            action="append",
        )

    def run(self, arguments: Namespace):
        from .run import run

        run(arguments)
