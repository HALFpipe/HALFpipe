# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import ArgumentParser, Namespace
from typing import Callable

from .base import Command


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
            required=True,
            dest="workdir",
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
            required=True,
        )
        argument_parser.add_argument(
            "--id-column",
            type=str,
            required=True,
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
            "--algorithm",
            type=str,
            nargs="+",
            action="extend",
        )

    def run(self, arguments: Namespace):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from ...collect.derivatives import collect_derivatives
        from ...design import group_design
        from ...model.contrast import ModelContrastSchema
        from ...model.variable import VariableSchema
        from ...result.aggregate import aggregate_results
        from ...result.bids.images import save_images
        from ...result.filter import filter_results
        from ...stats.algorithms import modelfit_aliases
        from ...stats.fit import fit
        from ...utils import logger
        from ...utils.future import chdir

        algorithms = arguments.algorithm
        if algorithms is None:
            return

        output_directory = Path(arguments.workdir)

        spreadsheet = arguments.spreadsheet

        variable_schema = VariableSchema()
        variables: list[dict] = [
            variable_schema.load(
                dict(
                    type="id",
                    name=arguments.id_column,
                )
            )
        ]

        contrast_schema = ModelContrastSchema()
        contrasts: list[dict] = list()

        if arguments.continuous_variable is not None:
            for name in arguments.continuous_variable:
                variables.append(
                    variable_schema.load(
                        dict(
                            type="continuous",
                            name=name,
                        )
                    )
                )
                contrasts.append(
                    contrast_schema.load(
                        dict(
                            type="infer",
                            variable=[name],
                        )
                    )
                )

        if arguments.categorical_variable is not None:
            for name, levels in zip(arguments.categorical_variable, arguments.levels):
                variables.append(
                    variable_schema.load(
                        dict(
                            type="categorical",
                            name=name,
                            levels=levels,
                        )
                    )
                )
                contrasts.append(
                    contrast_schema.load(
                        dict(
                            type="infer",
                            variable=[name],
                        )
                    )
                )

        results = list()
        for input_directory in arguments.input_directory:
            results.extend(collect_derivatives(Path(input_directory)))

        results = filter_results(
            results,
            require_one_of_images=["effect", "reho", "falff", "alff"],
            exclude_files=arguments.qc_exclude_files,
        )

        rename = arguments.rename
        if rename is not None:
            for key, from_value, to_value in rename:
                for result in results:
                    tags = result["tags"]
                    if key not in tags:
                        continue
                    if tags[key] == from_value:
                        tags[key] = to_value

        include = arguments.include
        if include is not None:
            for key, value in include:
                filtered_results = list()
                for result in results:
                    tags = result["tags"]
                    if key not in tags:
                        continue
                    if tags[key] == value:
                        filtered_results.append(result)
                results = filtered_results

        exclude = arguments.exclude
        if exclude is not None:
            filtered_results = list()
            for result in results:
                tags = result["tags"]

                should_include = True

                for key, value in exclude:
                    if key not in tags:
                        continue
                    if tags[key] == value:
                        should_include = False

                if should_include:
                    filtered_results.append(result)
                else:
                    logger.info(f"Excluding {tags}")
            results = filtered_results

        logger.debug(f"Including {len(results):d} sets of images")
        for result in results:
            tags = result["tags"]
            logger.debug(f"Including {tags}")

        results, _ = aggregate_results(results, "sub")

        group_level_results = list()

        aliases = dict(reho="effect", falff="effect", alff="effect")

        with TemporaryDirectory() as temporary_directory:
            for i, result in enumerate(results):
                tags = result["tags"]
                subjects = tags.pop("sub")

                logger.info(
                    f"Running model {tags} ({i + 1:d} of {len(results):d}) for {len(subjects)} inputs"
                )

                images = result.pop("images")

                for from_key, to_key in aliases.items():
                    if from_key in images:
                        images[to_key] = images.pop(from_key)

                cope_files = images.pop("effect")
                var_cope_files = images.pop("variance")
                mask_files = images.pop("mask")

                (regressor_list, contrast_list, _, contrast_names,) = group_design(
                    spreadsheet,
                    contrasts,
                    variables,
                    subjects,
                )

                model_path = Path(temporary_directory) / f"model-{i:03d}"
                model_path.mkdir(parents=True, exist_ok=True)

                with chdir(model_path):
                    output_files = fit(
                        cope_files,
                        var_cope_files,
                        mask_files,
                        regressor_list,
                        contrast_list,
                        algorithms,
                        8,
                    )

                    for from_key, to_key in modelfit_aliases.items():
                        if from_key in output_files:
                            output_files[to_key] = output_files.pop(from_key)

                    for i in range(len(contrast_names)):
                        group_level_result = result.copy()
                        if arguments.model_name is not None:
                            group_level_result["tags"]["model"] = arguments.model_name
                        group_level_result["images"] = {
                            key: value[i]
                            for key, value in output_files.items()
                            if isinstance(value[i], str)
                        }
                        group_level_results.append(group_level_result)

            save_images(group_level_results, output_directory)
