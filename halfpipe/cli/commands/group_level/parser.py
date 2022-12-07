# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from argparse import Namespace
from pathlib import Path

from ....logging import logger
from ....model.contrast import ModelContrastSchema
from ....model.filter import FilterSchema
from ....model.model import Model
from ....model.spec import Spec, load_spec
from ....model.variable import VariableSchema
from ....utils.format import format_like_bids, inflect_engine
from ....utils.path import resolve

variable_schema = VariableSchema()
contrast_schema = ModelContrastSchema()
filter_schema = FilterSchema()

DesignType = tuple[
    Path | None,
    list[Path],
    list[dict],
    list[dict],
    list[dict],
    list[dict],
]


def parse_group_level(
    arguments: Namespace,
    results: list[dict],
) -> DesignType:
    if arguments.from_spec:
        return _parse_from_spec(arguments, results)
    else:
        return _parse_from_arguments(arguments, results)


def _parse_from_spec(
    arguments: Namespace,
    results: list[dict],
) -> DesignType:
    workdir = resolve(arguments.input_directory[0], arguments.fs_root)

    spec: Spec | None = load_spec(workdir=workdir)

    if spec is None:
        raise ValueError(f'Cannot load spec file from "{workdir}"')

    model_name: str | None = arguments.model_name

    model: Model | None = None
    for m in spec.models:
        if m.across != "sub":
            continue  # skip lower level models
        if model_name is None or m.name == model_name:
            model = m
            break

    if model is None:
        if model_name is not None:
            raise ValueError(f'Model "{model_name}" not found')
        else:
            raise ValueError("Could not find a model to run")

    logger.info(f'Loading model "{model.name}" from spec file')

    spreadsheet: Path | str | None = getattr(model, "spreadsheet", None)
    if spreadsheet is not None:
        spreadsheet = Path(spreadsheet)

    variables: list[dict] = list()

    for f in spec.files:
        if f.datatype != "spreadsheet":
            continue
        if str(f.path) != str(spreadsheet):
            continue
        if "variables" not in f.metadata:
            continue
        variables = f.metadata["variables"]

    contrasts: list[dict] | None = getattr(model, "contrasts", None)
    if contrasts is None:
        contrasts = list()

    filters: list[dict] | None = getattr(model, "filters", None)
    if filters is None:
        filters = list()

    filtered_results = list()
    seen_inputs: set[str] = set()

    model_inputs: set[str] = set(map(format_like_bids, model.inputs))

    for result in results:
        tags = result["tags"]

        for key in ["feature", "model"]:
            value = tags.get(key)
            if value is None:
                continue
            value = format_like_bids(value)
            seen_inputs.add(value)
            if value in model_inputs:
                filtered_results.append(result)
                break
    results = filtered_results

    if len(results) == 0:
        seen_inputs_str = inflect_engine.join(
            [f'"{seen_input}"' for seen_input in sorted(seen_inputs)]
        )
        model_inputs_str = inflect_engine.join(
            [f'"{model_input}"' for model_input in sorted(model_inputs)],
            conj="or",
        )
        raise ValueError(
            f"Found inputs {seen_inputs_str}, but need one of {model_inputs_str}"
        )

    qc_exclude_files: list[Path] = [
        workdir / "exclude*.json",
        workdir / "reports" / "exclude*.json",
    ]

    if arguments.qc_exclude_files is not None:
        for qc_exclude_file in arguments.qc_exclude_files:
            qc_exclude_files.append(resolve(qc_exclude_file, arguments.fs_root))

    return spreadsheet, qc_exclude_files, variables, contrasts, filters, results


def _parse_from_arguments(
    arguments: Namespace,
    results: list[dict],
) -> DesignType:
    spreadsheet: Path = resolve(arguments.spreadsheet, arguments.fs_root)

    variables: list[dict] = list()
    if arguments.id_column is not None:
        variables.append(
            variable_schema.load(
                dict(
                    type="id",
                    name=arguments.id_column,
                )
            )
        )

    filters: list[dict] = list()
    if arguments.fd_mean_cutoff is not None:
        filters.append(
            filter_schema.load(
                dict(
                    type="cutoff",
                    action="exclude",
                    field="fd_mean",
                    cutoff=arguments.fd_mean_cutoff,
                )
            )
        )
    if arguments.fd_perc_cutoff is not None:
        filters.append(
            filter_schema.load(
                dict(
                    type="cutoff",
                    action="exclude",
                    field="fd_perc",
                    cutoff=arguments.fd_perc_cutoff,
                )
            )
        )

    contrasts: list[dict] = list()

    continuous_variable = arguments.continuous_variable
    if continuous_variable is not None:
        for name in continuous_variable:
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

    categorical_variable = arguments.categorical_variable
    if categorical_variable is not None:
        for name, levels in zip(categorical_variable, arguments.levels):
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

    missing_value_strategy = arguments.missing_value_strategy
    if missing_value_strategy == "listwise-deletion":
        for variable in variables:
            name = variable["name"]
            filters.append(
                filter_schema.load(
                    dict(
                        type="missing",
                        action="exclude",
                        variable=name,
                    )
                )
            )

    qc_exclude_files: list[Path] = list()
    if arguments.qc_exclude_files is not None:
        for qc_exclude_file in arguments.qc_exclude_files:
            qc_exclude_files.append(resolve(qc_exclude_file, arguments.fs_root))

    return spreadsheet, qc_exclude_files, variables, contrasts, filters, results
