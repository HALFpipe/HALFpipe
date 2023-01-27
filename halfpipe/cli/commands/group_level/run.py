# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import Namespace
from collections import defaultdict
from contextlib import chdir
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from nipype.interfaces import fsl
from tqdm.auto import tqdm

from ....collect.derivatives import collect_derivatives
from ....design import group_design, intercept_only_design, make_design_tsv
from ....interfaces.image_maths.merge import merge, merge_mask
from ....logging import logger
from ....result.aggregate import aggregate_results
from ....result.bids.images import save_images
from ....result.filter import filter_results
from ....stats.algorithms import algorithms as all_algorithms
from ....stats.algorithms import modelfit_aliases
from ....stats.fit import fit
from ....utils.format import format_like_bids, format_tags
from ....utils.hash import b32_digest
from ....utils.multiprocessing import Pool
from ....utils.path import resolve
from .parser import parse_group_level

aliases = dict(reho="effect", falff="effect", alff="effect")


def run(arguments: Namespace):
    if arguments.workdir is not None:
        output_directory = Path(arguments.workdir)
    else:
        output_directory = Path(arguments.input_directory[0])
    output_directory = resolve(output_directory, arguments.fs_root)

    exports = arguments.export
    if exports is not None:
        raise NotImplementedError

    algorithms = arguments.algorithm
    if algorithms is None:
        algorithms = list(all_algorithms.keys())

    results = list()
    for input_directory in arguments.input_directory:
        results.extend(collect_derivatives(resolve(input_directory, arguments.fs_root)))

    if len(results) == 0:
        raise ValueError("No inputs found")

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

    # other criteria
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

    # `--rename`
    rename = arguments.rename
    if rename is not None:
        for key, from_value, to_value in rename:
            for result in results:
                tags = result["tags"]
                if key not in tags:
                    continue
                if tags[key] == from_value:
                    tags[key] = to_value

    with (
        TemporaryDirectory() as temporary_directory,
        chdir(temporary_directory),
    ):
        aggregate: list[str] = arguments.aggregate
        if aggregate is not None:
            for key in aggregate:
                results = within(results, key, arguments.nipype_n_procs)

        between(
            results,
            spreadsheet,
            contrasts,
            variables,
            algorithms,
            output_directory,
            arguments.nipype_n_procs,
            arguments.model_name,
        )


def within(
    results: list,
    key: str,
    n_procs: int,
) -> list:
    results, bypass = aggregate_results(results, key)

    logger.log(25, f'Will run {len(results):d} models at level "{key}"')
    with Pool(processes=n_procs) as pool:
        results = list(
            tqdm(
                pool.imap_unordered(_within, results),
                total=len(results),
                desc=f'level "{key}"',
            )
        )

    results.extend(bypass)

    return results


def between(
    results: list,
    spreadsheet,
    contrasts: list,
    variables: list,
    algorithms: list[str],
    output_directory: Path,
    n_procs: int,
    model_name: str | None = None,
):
    results, _ = aggregate_results(results, "sub")

    if len(results) == 0:
        raise ValueError("No inputs found")

    logger.log(25, f"Will run {len(results):d} group-level models")
    for i, result in enumerate(results):
        _between(
            i,
            result,
            spreadsheet,
            contrasts,
            variables,
            algorithms,
            n_procs,
            model_name,
            output_directory,
        )


def _within(result: dict):
    key = b32_digest(result)[:8]

    model_directory = Path.cwd() / f"model-{key}"
    model_directory.mkdir(exist_ok=False, parents=True)

    tags = {
        key: value for key, value in result["tags"].items() if isinstance(value, str)
    }  # filter out list fields

    images = result.pop("images")

    for from_key, to_key in aliases.items():
        if from_key in images:
            images[to_key] = images.pop(from_key)

    cope_files = images.pop("effect")
    var_cope_files = images.pop("variance")
    mask_files = images.pop("mask")

    with chdir(model_directory):
        cope_file = merge(cope_files, "t")
        var_cope_file = merge(var_cope_files, "t")
        mask_file = merge_mask(mask_files)

        n = len(cope_files)
        (regressors, contrasts, _, _) = intercept_only_design(n)
        multiple_regress_design = fsl.MultipleRegressDesign(
            regressors=regressors,
            contrasts=contrasts,
        ).run()
        assert multiple_regress_design.outputs is not None

        flameo = fsl.FLAMEO(
            cope_file=cope_file,
            var_cope_file=var_cope_file,
            mask_file=mask_file,
            run_mode="fe",
            design_file=multiple_regress_design.outputs.design_mat,
            t_con_file=multiple_regress_design.outputs.design_con,
            cov_split_file=multiple_regress_design.outputs.design_grp,
        ).run()
        assert flameo.outputs is not None

    cope_file = flameo.outputs.copes
    var_cope_file = flameo.outputs.var_copes

    images = dict(
        effect=cope_file,
        variance=var_cope_file,
        mask=mask_file,
    )

    result["tags"] = tags
    result["images"] = images

    return result


def _between(
    i,
    result,
    spreadsheet,
    contrasts,
    variables,
    algorithms,
    n_procs,
    model_name,
    output_directory,
):
    model_directory = Path.cwd() / f"model-{i:02d}"
    model_directory.mkdir(exist_ok=True, parents=True)

    tags = result["tags"]
    subjects = tags.pop("sub")

    # remove lower level tags
    for key in ["contrast", "model"]:
        if key in tags:
            del tags[key]

    logger.log(
        25,
        f"Running model {i + 1:d} with tags {format_tags(tags)} for {len(subjects)} subjects",
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

    with chdir(model_directory):
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
            n_procs,
        )

    for from_key, to_key in modelfit_aliases.items():
        if from_key in output_files:
            output_files[to_key] = output_files.pop(from_key)

    images = {
        key: value for key, value in output_files.items() if isinstance(value, str)
    }
    images["design_matrix"] = str(design_tsv)
    images["contrast_matrix"] = str(contrast_tsv)

    model_results = list()

    model_result = deepcopy(result)
    if model_name is not None:
        model_result["tags"]["model"] = model_name
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
        if model_name is not None:
            model_result["tags"]["model"] = model_name
        model_result["images"] = images
        model_results.append(model_result)

    save_images(model_results, output_directory)
