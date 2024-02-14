# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import Namespace
from collections import defaultdict
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory

from ....collect.derivatives import collect_halfpipe_derivatives
from ....logging import logger
from ....result.aggregate import aggregate_results
from ....result.base import ResultDict
from ....utils.format import format_like_bids
from ....utils.path import resolve
from ....workdir import init_workdir
from .aggregate import apply_aggregate
from .between import BetweenBase
from .derived import apply_derived
from .design import DesignBase, apply_from_arguments, apply_from_spec

aliases = dict(reho="effect", falff="effect", alff="effect")


def run(arguments: Namespace):
    """Top level method for the group-level command"""
    if arguments.output_directory is not None:
        output_directory = Path(arguments.output_directory)
    elif arguments.workdir is not None:
        output_directory = Path(arguments.workdir)
    else:
        output_directory = Path(arguments.input_directory[0])
    output_directory = init_workdir(output_directory, arguments.fs_root)

    # Index the input directories
    input_directories = [resolve(input_directory, arguments.fs_root) for input_directory in arguments.input_directory]
    results: list[ResultDict] = collect_halfpipe_derivatives(input_directories, num_threads=arguments.nipype_n_procs)

    if len(results) == 0:
        raise ValueError("No inputs found")

    results = apply_include(arguments.include, arguments.include_list, results)
    results = apply_exclude(arguments.exclude, arguments.exclude_list, results)

    if arguments.from_spec:
        design_bases = apply_from_spec(arguments, results)
    else:
        design_bases = apply_from_arguments(arguments, results)

    for design_base in design_bases:
        design_base.filter_results()
        apply_design(arguments, design_base, output_directory)


def apply_list_files(
    target: list[tuple[str, str]],
    file_list: list[tuple[str, str]],
) -> None:
    for key, file_name in file_list:
        with Path(file_name).open("rt") as file_handle:
            for line in file_handle:
                line = line.strip()
                if not line:
                    continue
                target.append((key, format_like_bids(line)))


def apply_include(
    include: list[tuple[str, str]] | None,
    include_list: list[tuple[str, str]] | None,
    results: list[ResultDict],
) -> list[ResultDict]:
    """Handle the `--include` argument"""
    if include is None:
        include = list()
    if include_list is None:
        include_list = list()

    apply_list_files(include, include_list)

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
        raise ValueError('No inputs remain after "--include" was applied')

    return results


def apply_exclude(
    exclude: list[tuple[str, str]] | None,
    exclude_list: list[tuple[str, str]] | None,
    results: list[ResultDict],
) -> list[ResultDict]:
    """Handle the `--exclude` argument"""
    if exclude is None:
        exclude = list()
    if exclude_list is None:
        exclude_list = list()

    apply_list_files(exclude, exclude_list)

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
        raise ValueError('No inputs remain after "--exclude" was applied')

    return results


def apply_rename(rename: list[tuple[str, str, str]] | None, results: list[ResultDict]) -> list[ResultDict]:
    """Handle the `--rename` argument"""
    if rename is None:
        return results
    for key, from_value, to_value in rename:
        for result in results:
            tags = result["tags"]
            if key not in tags:
                continue
            if tags[key] == from_value:
                tags[key] = to_value

    return results


def apply_design(arguments: Namespace, design_base: DesignBase, output_directory: Path):
    """The calculations to perform for each model that we run"""
    design_base.results = apply_rename(arguments.rename, design_base.results)
    between_base = BetweenBase(
        arguments,
        output_directory,
    )
    with (
        TemporaryDirectory(prefix="group-level") as temporary_directory,
        chdir(temporary_directory),
    ):
        # Within-subject aggregation step
        apply_aggregate(design_base, num_threads=arguments.nipype_n_procs)

        # Add derived variables and images
        apply_derived(arguments, design_base)

        # Between-subject aggregation step
        design_base.results, _ = aggregate_results(design_base.results, "sub")
        if len(design_base.results) == 0:
            raise ValueError("No inputs found")

        logger.info(f"Will process {len(design_base.results):d} variables")
        for i, result in enumerate(design_base.results):
            model_directory = Path.cwd() / f"variable-{i + 1:02d}"
            model_directory.mkdir(exist_ok=True, parents=True)

            with chdir(model_directory):
                between_base.apply(
                    result,
                    design_base,
                )
    between_base.write_outputs()
