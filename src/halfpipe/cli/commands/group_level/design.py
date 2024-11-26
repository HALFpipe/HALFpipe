# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from argparse import Namespace
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Self

import pandas as pd

from ....design import prepare_data_frame
from ....logging import logger
from ....model.spec import Spec, load_spec
from ....result.base import ResultDict
from ....result.filter import filter_results
from ....utils.format import format_like_bids, inflect_engine
from ....utils.path import resolve
from .base import contrast_schema, filter_schema, variable_schema


@dataclass
class DesignBase:
    model_name: str | None
    data_frame: pd.DataFrame | None
    qc_exclude_files: list[Path]
    variables: list[dict]
    contrasts: list[dict]
    filters: list[dict]
    results: list[ResultDict]
    aggregate: list[str] | None

    variable_sets: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def filter_results(self) -> None:
        self.results = filter_results(
            self.results,
            filter_dicts=self.filters,
            # Require images we can do statistics on
            require_one_of_images=["effect", "reho", "falff", "alff"],
            exclude_files=self.qc_exclude_files,
            spreadsheet=self.data_frame,
            variable_dicts=self.variables,
        )
        if len(self.results) == 0:
            raise ValueError("No images remain after filtering")

    @classmethod
    def from_spreadsheet(
        cls,
        model_name: str | None,
        spreadsheet: Path | None,
        qc_exclude_files: list[Path],
        variables: list[dict],
        contrasts: list[dict],
        filters: list[dict],
        results: list[ResultDict],
        aggregate: list[str] | None,
    ) -> Self:
        if spreadsheet is None:
            data_frame = None
        else:
            data_frame = prepare_data_frame(spreadsheet, variables)
            column_info = inflect_engine.join([f'"{column}"' for column in data_frame.columns])
            logger.info(f"Initializing design base with variables {column_info}")
        return cls(
            model_name,
            data_frame,
            qc_exclude_files,
            variables,
            contrasts,
            filters,
            results,
            aggregate,
        )

    def add_variable(
        self,
        name: str,
        series: pd.Series | None = None,
        prefix: str | None = None,
    ) -> None:
        """
        Adds a new variable as a columnto the data_frame.

        Args:
            name (str): The name of the variable.
            series (pd.Series): The data for the variable.

        Raises:
            ValueError: If the design does not have a `data_frame`.

        Returns:
            None
        """
        if self.data_frame is None:
            raise ValueError("Cannot add variable to design without `data_frame`")
        logger.info(f'Adding variable "{name}" to design base')
        # Add variable to data frame
        if prefix is not None:
            prefixed_name = f"{prefix}_{name}"
            self.variable_sets[name].add(prefixed_name)
            name = prefixed_name
        if series is not None:
            series_frame = pd.DataFrame({name: series}, dtype=float)
            self.data_frame = self.data_frame.combine_first(series_frame)
        # Add contrasts for new variable
        contrast = contrast_schema.load(
            dict(
                type="infer",
                variable=[name],
            )
        )
        if not isinstance(contrast, dict):
            raise RuntimeError
        self.contrasts.append(contrast)

    def drop_variable(
        self,
        name: str,
    ) -> pd.Series | None:
        if self.data_frame is None:
            raise ValueError("Cannot drop variable from design without `data_frame`")
        logger.info(f'Removing variable "{name}" from design base')
        # Remove contrasts for the variable
        self.contrasts = [
            contrast for contrast in self.contrasts if all(variable != name for variable in contrast["variable"])
        ]
        if name in self.data_frame:
            return self.data_frame.pop(name)
        return None


def apply_from_spec(
    arguments: Namespace,
    results: list[ResultDict],
) -> Generator[DesignBase, None, None]:
    workdir = resolve(arguments.input_directory[0], arguments.fs_root)

    spec: Spec | None = load_spec(workdir=workdir)

    if spec is None:
        raise ValueError(f'Cannot load spec file from "{workdir}"')

    model_name: str | None = arguments.model_name
    for model in spec.models:
        if model.across != "sub":
            continue  # skip lower level models
        if model_name is not None and model.name != model_name:
            continue

        logger.info(f'Loading model "{model.name}" from spec file')

        spreadsheet: Path | str | None = getattr(model, "spreadsheet", None)
        if spreadsheet is not None:
            spreadsheet = Path(spreadsheet)

        variables: list[dict] = list()
        for file_obj in spec.files:
            if file_obj.datatype != "spreadsheet":
                continue
            if str(file_obj.path) != str(spreadsheet):
                continue
            if "variables" not in file_obj.metadata:
                continue
            variables = file_obj.metadata["variables"]

        contrasts: list[dict] | None = getattr(model, "contrasts", None)
        if contrasts is None:
            contrasts = list()
        filters: list[dict] | None = getattr(model, "filters", None)
        if filters is None:
            filters = list()

        seen_inputs: set[str] = set()
        model_inputs: set[str] = set(map(format_like_bids, model.inputs))
        filtered_results: list[ResultDict] = list()
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
            # Print a nice error message
            seen_inputs_str = inflect_engine.join([f'"{seen_input}"' for seen_input in sorted(seen_inputs)])
            model_inputs_str = inflect_engine.join(
                [f'"{model_input}"' for model_input in sorted(model_inputs)],
                conj="or",
            )
            raise ValueError(f"Found inputs {seen_inputs_str}, but need one of {model_inputs_str}")

        qc_exclude_files: list[Path] = [
            workdir / "exclude*.json",
            workdir / "reports" / "exclude*.json",
        ]
        if arguments.qc_exclude_files is not None:
            for qc_exclude_file in arguments.qc_exclude_files:
                qc_exclude_files.append(resolve(qc_exclude_file, arguments.fs_root))

        # TODO: Support getting fixed-effects aggregate steps from the spec file
        aggregate: list[str] | None = list()

        yield DesignBase.from_spreadsheet(
            model.name,
            spreadsheet,
            qc_exclude_files,
            variables,
            contrasts,
            filters,
            results,
            aggregate,
        )


def apply_from_arguments(
    arguments: Namespace,
    results: list[ResultDict],
) -> Generator[DesignBase, None, None]:
    spreadsheet: Path | None = None
    if arguments.spreadsheet is not None:
        spreadsheet = resolve(arguments.spreadsheet, arguments.fs_root)

    variables: list[dict] = list()
    contrasts: list[dict] = list()

    if arguments.id_column is not None:
        variable = variable_schema.load(
            dict(
                type="id",
                name=arguments.id_column,
            )
        )
        if not isinstance(variable, dict):
            raise RuntimeError
        variables.append(variable)

    filters: list[dict] = list()
    if arguments.fd_mean_cutoff is not None:
        filter = filter_schema.load(
            dict(
                type="cutoff",
                action="exclude",
                field="fd_mean",
                cutoff=arguments.fd_mean_cutoff,
            )
        )
        if not isinstance(filter, dict):
            raise RuntimeError
        filters.append(filter)
    if arguments.fd_perc_cutoff is not None:
        filter = filter_schema.load(
            dict(
                type="cutoff",
                action="exclude",
                field="fd_perc",
                cutoff=arguments.fd_perc_cutoff,
            )
        )
        if not isinstance(filter, dict):
            raise RuntimeError
        filters.append(filter)

    def add_variable(type: str, name: str, **variable_kwargs) -> None:
        variable = variable_schema.load(
            dict(
                type=type,
                name=name,
                **variable_kwargs,
            )
        )
        if not isinstance(variable, dict):
            raise RuntimeError
        variables.append(variable)
        contrast = contrast_schema.load(
            dict(
                type="infer",
                variable=[name],
            )
        )
        if not isinstance(contrast, dict):
            raise RuntimeError
        contrasts.append(contrast)

    continuous_variable = arguments.continuous_variable
    if continuous_variable is not None:
        for name in continuous_variable:
            add_variable("continuous", name)
    categorical_variable = arguments.categorical_variable
    if categorical_variable is not None:
        for name, levels in zip(categorical_variable, arguments.levels, strict=False):
            add_variable("categorical", name, levels=levels)
    for json_data in arguments.contrast or list():
        contrast = contrast_schema.loads(json_data)
        if not isinstance(contrast, dict):
            raise RuntimeError
        contrasts.append(contrast)

    missing_value_strategy = arguments.missing_value_strategy
    if missing_value_strategy == "listwise-deletion":
        for variable in variables:
            name = variable["name"]
            filter = filter_schema.load(
                dict(
                    type="missing",
                    action="exclude",
                    variable=name,
                )
            )
            if not isinstance(filter, dict):
                raise RuntimeError
            filters.append(filter)

    qc_exclude_files: list[Path] = list()
    if arguments.qc_exclude_files is not None:
        for qc_exclude_file in arguments.qc_exclude_files:
            qc_exclude_files.append(resolve(qc_exclude_file, arguments.fs_root))

    aggregate = arguments.aggregate

    yield DesignBase.from_spreadsheet(
        arguments.model_name,
        spreadsheet,
        qc_exclude_files,
        variables,
        contrasts,
        filters,
        results,
        aggregate,
    )
