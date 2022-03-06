# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose
from typing import Callable

import numpy as np
import pandas as pd
from nipype.interfaces.base import (
    BaseInterfaceInputSpec,
    File,
    SimpleInterface,
    isdefined,
    traits,
)

from ...ingest.exclude import Decision, QCDecisionMaker
from ...ingest.spreadsheet import read_spreadsheet
from ...utils import inflect_engine, logger
from ...utils.format import format_tags, normalize_subject
from .base import Continuous, ResultdictsOutputSpec


def _get_data_frame(file_path, variable_dicts):
    data_frame = read_spreadsheet(file_path, dtype=object)

    id_column = None
    for variable_dict in variable_dicts:
        if variable_dict.get("type") == "id":
            id_column = variable_dict.get("name")
            break

    if id_column is None:
        raise ValueError(f'Column "{id_column}" not found')

    data_frame[id_column] = pd.Series(data_frame[id_column], dtype=str)
    data_frame[id_column] = list(map(normalize_subject, data_frame[id_column]))
    data_frame = data_frame.set_index(id_column)

    return data_frame


def _get_categorical_dict(data_frame, variable_dicts):
    categorical_columns = []
    for variable_dict in variable_dicts:
        if variable_dict.get("type") == "categorical":
            categorical_columns.append(variable_dict.get("name"))

    categorical_data_frame = data_frame[categorical_columns].astype(str)
    return categorical_data_frame.to_dict()


def _make_group_filterfun(
    filter_dict: dict, categorical_dict: dict, model_desc: str
) -> Callable[[dict], bool] | None:
    variable = filter_dict.get("variable")
    if variable not in categorical_dict:
        return None

    levels = filter_dict.get("levels")
    if levels is None or len(levels) == 0:
        return None

    variable_dict = categorical_dict[variable]
    selected_subjects = frozenset(
        subject for subject, value in variable_dict.items() if value in levels
    )

    levelsdesc = inflect_engine.join([f'"{v}"' for v in levels], conj="or")

    action = filter_dict["action"]

    if action == "include":

        def group_include_filterfun(d):
            subject = d.get("tags").get("sub")
            subject = normalize_subject(subject)

            res = subject in selected_subjects

            if res is False:
                logger.info(
                    f'Excluding subject "{subject}" {model_desc}because "{variable}" is not {levelsdesc}'
                )

            return res

        return group_include_filterfun

    elif action == "exclude":

        def group_exclude_filterfun(d):
            subject = d["tags"].get("sub")
            subject = normalize_subject(subject)

            res = subject not in selected_subjects

            if res is False:
                logger.info(
                    f'Excluding subject "{subject}" {model_desc}because "{variable}" is {levelsdesc}'
                )

            return res

        return group_exclude_filterfun

    else:
        raise ValueError(f'Invalid action "{action}"')


def _make_missing_filterfun(
    filter_dict: dict, data_frame: pd.DataFrame, model_desc: str
) -> Callable[[dict], bool] | None:
    variable = filter_dict["variable"]
    if variable not in data_frame.columns:
        return None

    assert filter_dict["action"] == "exclude"

    is_finite = pd.notnull(data_frame[variable])
    assert isinstance(is_finite, pd.Series)

    selected_subjects = frozenset(is_finite.index[is_finite])

    def missing_filterfun(d):
        subject = d["tags"].get("sub")
        subject = normalize_subject(subject)

        res = subject in selected_subjects

        if res is False:
            logger.warning(
                f'Excluding subject "{subject}" {model_desc}because "{variable}" is missing'
            )

        return res

    return missing_filterfun


def _make_cutoff_filterfun(
    filter_dict: dict, model_desc: str
) -> Callable[[dict], bool] | None:
    assert filter_dict["action"] == "exclude"

    cutoff = filter_dict["cutoff"]
    assert isinstance(cutoff, float)

    filter_field = filter_dict["field"]

    if filter_field == "fd_perc" and cutoff < 1 and not isclose(cutoff, 1):
        logger.warning(
            f'The cutoff for "fd_perc" of {cutoff:f} was re-scaled to {cutoff * 100} percent'
        )
        cutoff *= 100

    def cutoff_filterfun(d):
        val = d["vals"].get(filter_field, np.inf)

        if isinstance(val, float):
            x: float = val
        else:
            continuous = Continuous.load(val)
            if continuous is not None:
                x = continuous.mean
            else:
                raise ValueError(f'Cannot filter by "{val}"')

        res = x <= cutoff

        if res is False:
            tags = d["tags"]
            logger.warning(
                f"Excluding ({format_tags(tags)}) {model_desc}"
                f'because "{filter_field}" is larger than {cutoff:f}'
            )

        return res

    return cutoff_filterfun


def _parse_filter_dict(
    filter_dict: dict,
    categorical_dict: dict = dict(),
    data_frame: pd.DataFrame | None = None,
    model_name: str | None = None,
) -> Callable[[dict], bool] | None:
    model_desc = ""
    if model_name is not None:
        model_desc = f'from model "{model_name}" '

    filter_type = filter_dict.get("type")
    if filter_type == "group":
        return _make_group_filterfun(filter_dict, categorical_dict, model_desc)

    elif filter_type == "missing":
        if data_frame is None:
            raise ValueError("Missing data_frame")
        return _make_missing_filterfun(filter_dict, data_frame, model_desc)

    elif filter_type == "cutoff":
        return _make_cutoff_filterfun(filter_dict, model_desc)

    return None


class FilterResultdictsInputSpec(BaseInterfaceInputSpec):
    in_dicts = traits.List(traits.Dict(traits.Str(), traits.Any()), mandatory=True)

    model_name = traits.Str()
    filter_dicts = traits.List(traits.Any(), desc="filter list")
    variable_dicts = traits.List(traits.Any(), desc="variable list")
    spreadsheet = File(desc="spreadsheet", exists=True)
    require_one_of_images = traits.List(
        traits.Str(), desc="only keep resultdicts that have at least one of these keys"
    )
    exclude_files = traits.List(traits.Str())


class FilterResultdicts(SimpleInterface):
    input_spec = FilterResultdictsInputSpec
    output_spec = ResultdictsOutputSpec

    def _run_interface(self, runtime):
        out_dicts: list[dict[str, dict]] = self.inputs.in_dicts.copy()

        data_frame = None
        categorical_dict = None
        if isdefined(self.inputs.spreadsheet) and isdefined(self.inputs.variable_dicts):
            data_frame = _get_data_frame(
                self.inputs.spreadsheet, self.inputs.variable_dicts
            )
            categorical_dict = _get_categorical_dict(
                data_frame, self.inputs.variable_dicts
            )

        model_name = None
        if isdefined(self.inputs.model_name):
            model_name = self.inputs.model_name

        filter_dicts: list[dict] = list()
        if isdefined(self.inputs.filter_dicts):
            filter_dicts.extend(self.inputs.filter_dicts)

        kwargs = dict(
            data_frame=data_frame,
            categorical_dict=categorical_dict,
            model_name=model_name,
        )

        if isdefined(self.inputs.require_one_of_images):
            require_one_of_images = self.inputs.require_one_of_images
            if len(require_one_of_images) > 0:
                out_dicts = [
                    out_dict
                    for out_dict in out_dicts
                    if isinstance(out_dict, dict)
                    and any(
                        key in out_dict.get("images") for key in require_one_of_images
                    )
                ]
        for filter_dict in filter_dicts:
            filter_fun = _parse_filter_dict(filter_dict, **kwargs)
            if filter_fun is not None:
                out_dicts = list(filter(filter_fun, out_dicts))

        exclude_files = self.inputs.exclude_files
        if isdefined(exclude_files):
            decision_maker = QCDecisionMaker(exclude_files)

            out_dicts = [
                out_dict
                for out_dict in out_dicts
                if decision_maker.get(out_dict["tags"]) is Decision.INCLUDE
            ]

        self._results["resultdicts"] = out_dicts

        return runtime
