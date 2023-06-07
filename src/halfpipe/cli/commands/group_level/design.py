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
    contrasts: list[dict]
    filters: list[dict]
    results: list[ResultDict]
    aggregate: list[str] | None

    variable_sets: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

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

        results = filter_results(
            results,
            filter_dicts=filters,
            # Require images we can do statistics on
            require_one_of_images=["effect", "reho", "falff", "alff"],
            exclude_files=qc_exclude_files,
            spreadsheet=data_frame,
            variable_dicts=variables,
        )
        if len(results) == 0:
            raise ValueError("No images remain after filtering")
        return cls(
            model_name,
            data_frame,
            qc_exclude_files,
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

        # Add variable to data frame
        if prefix is not None:
            prefixed_name = f"{prefix}_{name}"
            self.variable_sets[name].add(prefixed_name)
            name = prefixed_name
        if series is not None:
            series_frame = pd.DataFrame({name: series})
            self.data_frame = self.data_frame.combine_first(series_frame)
        # Add contrasts for new variable
        self.contrasts.append(
            contrast_schema.load(
                dict(
                    type="infer",
                    variable=[name],
                )
            )
        )

    def drop_variable(
        self,
        name: str,
    ) -> pd.Series | None:
        if self.data_frame is None:
            raise ValueError("Cannot drop variable from design without `data_frame`")
        # Remove contrasts for the variable
        self.contrasts = [
            contrast
            for contrast in self.contrasts
            if all(variable != name for variable in contrast["variable"])
        ]
        if name in self.data_frame:
            return self.data_frame.pop(name)
        return None


def apply_from_spec(
    arguments: Namespace,
    results: list[dict],
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
    results: list[dict],
) -> Generator[DesignBase, None, None]:
    spreadsheet: Path | None = None
    if arguments.spreadsheet is not None:
        spreadsheet = resolve(arguments.spreadsheet, arguments.fs_root)

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
