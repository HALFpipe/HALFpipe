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
            "--export",
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

    def run(self, arguments: Namespace):
        from collections import defaultdict
        from copy import deepcopy
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from ....collect.derivatives import collect_derivatives
        from ....design import group_design, intercept_only_design, make_design_tsv
        from ....logging import logger
        from ....result.aggregate import aggregate_results
        from ....result.bids.images import save_images
        from ....result.filter import filter_results
        from ....stats.algorithms import algorithms as all_algorithms
        from ....stats.algorithms import modelfit_aliases
        from ....stats.fit import fit
        from ....utils.format import format_like_bids, format_tags
        from ....utils.future import chdir
        from ....utils.path import resolve
        from .parser import parse_group_level

        if arguments.workdir is not None:
            output_directory = Path(arguments.workdir)
        else:
            output_directory = Path(arguments.input_directory[0])
        output_directory = resolve(output_directory, arguments.fs_root)

        results = list()
        for input_directory in arguments.input_directory:
            results.extend(
                collect_derivatives(resolve(input_directory, arguments.fs_root))
            )

        if len(results) == 0:
            raise ValueError("No inputs found")

        (
            spreadsheet,
            qc_exclude_files,
            variables,
            contrasts,
            filters,
            results,
        ) = parse_group_level(arguments, results)

        results = filter_results(
            results,
            filter_dicts=filters,
            require_one_of_images=["effect", "reho", "falff", "alff"],
            exclude_files=qc_exclude_files,
            spreadsheet=spreadsheet,
            variable_dicts=variables,
        )

        if len(results) == 0:
            raise ValueError("No images remain after filtering")

        rename = arguments.rename
        if rename is not None:
            for key, from_value, to_value in rename:
                for result in results:
                    tags = result["tags"]
                    if key not in tags:
                        continue
                    if tags[key] == from_value:
                        tags[key] = to_value

        # `--include`
        include = list()
        if arguments.include is not None:
            include.extend(arguments.include)

        include_groups: dict[str, set[str]] = defaultdict(set)
        for key, value in include:
            include_groups[key].add(format_like_bids(value))
        for key, values in include_groups.items():
            filtered_results = list()
            for result in results:
                tags = result["tags"]
                if key not in tags:
                    continue
                if format_like_bids(tags[key]) in values:
                    filtered_results.append(result)
            results = filtered_results

        if len(results) == 0:
            raise ValueError('No images remain after "--include" was applied')

        # `--exclude`
        exclude: list[tuple[str, str]] = list()
        if arguments.exclude is not None:
            exclude.extend(arguments.exclude)

        filtered_results = list()
        for result in results:
            tags = result["tags"]
            _include_flag = True
            for key, value in exclude:
                if key not in tags:
                    continue
                if tags[key] == value:
                    _include_flag = False
            if _include_flag:
                filtered_results.append(result)
            else:
                logger.info(f"Excluding {tags}")
        results = filtered_results

        if len(results) == 0:
            raise ValueError('No images remain after "--exclude" was applied')

        across: list[str] = arguments.aggregate
        if across is not None and len(across) > 0 and across != ["sub"]:
            raise NotImplementedError

        # cross-subject processing
        results, _ = aggregate_results(results, "sub")

        aliases = dict(reho="effect", falff="effect", alff="effect")

        exports = arguments.export
        if exports is not None:
            raise NotImplementedError

        algorithms = arguments.algorithm
        if algorithms is None:
            algorithms = list(all_algorithms.keys())

        if len(results) == 0:
            raise ValueError("No inputs found")

        for i, result in enumerate(results):
            tags = result["tags"]
            subjects = tags.pop("sub")

            # remove lower level contrast label
            if "contrast" in tags:
                del tags["contrast"]

            logger.log(
                25,
                f"Running model {i + 1:d} of {len(results):d} "
                f"with tags {format_tags(tags)} for {len(subjects)} subjects",
            )

            images = result.pop("images")

            for from_key, to_key in aliases.items():
                if from_key in images:
                    images[to_key] = images.pop(from_key)

            cope_files = images.pop("effect")
            var_cope_files = images.pop("variance")
            mask_files = images.pop("mask")

            if spreadsheet is not None:
                (regressor_list, contrast_list, _, contrast_names) = group_design(
                    spreadsheet,
                    contrasts,
                    variables,
                    subjects,
                )
            else:
                (
                    regressor_list,
                    contrast_list,
                    _,
                    contrast_names,
                ) = intercept_only_design(len(subjects))

            with TemporaryDirectory() as temporary_directory:
                model_path = Path(temporary_directory)

                with chdir(model_path):
                    design_tsv, contrast_tsv = make_design_tsv(
                        regressor_list, contrast_list, subjects
                    )

                    output_files = fit(
                        cope_files,
                        var_cope_files,
                        mask_files,
                        regressor_list,
                        contrast_list,
                        algorithms,
                        arguments.nipype_n_procs,
                    )

                for from_key, to_key in modelfit_aliases.items():
                    if from_key in output_files:
                        output_files[to_key] = output_files.pop(from_key)

                images = {
                    key: value
                    for key, value in output_files.items()
                    if isinstance(value, str)
                }
                images["design_matrix"] = str(design_tsv)
                images["contrast_matrix"] = str(contrast_tsv)

                model_results = list()

                model_result = deepcopy(result)
                if arguments.model_name is not None:
                    model_result["tags"]["model"] = arguments.model_name
                model_result["images"] = images
                model_results.append(model_result)

                for i, contrast_name in enumerate(contrast_names):
                    images = {
                        key: value[i]
                        for key, value in output_files.items()
                        if isinstance(value, list) and isinstance(value[i], str)
                    }
                    if len(images) == 0:
                        continue
                    model_result = deepcopy(result)
                    model_result["tags"]["contrast"] = contrast_name
                    if arguments.model_name is not None:
                        model_result["tags"]["model"] = arguments.model_name
                    model_result["images"] = images
                    model_results.append(model_result)

                save_images(model_results, output_directory)
