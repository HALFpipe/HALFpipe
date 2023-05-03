# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import pandas as pd

from ..design import prepare_data_frame
from ..exclude import Decision, QCDecisionMaker
from ..logging import logger
from ..utils.format import format_tags, inflect_engine, normalize_subject
from .base import ResultDict
from .variables import Continuous


def get_categorical_dict(data_frame, variable_dicts):
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
        normalize_subject(subject)
        for subject, value in variable_dict.items()
        if value in levels
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

    selected_subjects = frozenset(map(normalize_subject, is_finite.index[is_finite]))

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

    def cutoff_filterfun(d: dict) -> bool:
        tags = d["tags"]
        vals = d.get("vals")

        if vals is None:
            logger.warning(
                f"Excluding ({format_tags(tags)}) {model_desc}"
                f'because "{filter_field}" is missing. '
            )
            return False
        val = vals.get(filter_field, np.inf)

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
            logger.warning(
                f"Excluding ({format_tags(tags)}) {model_desc}"
                f'because "{filter_field}" is larger than {cutoff:f}'
            )

        return res

    return cutoff_filterfun


def parse_filter_dict(
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


def filter_results(
    results: list[ResultDict],
    filter_dicts: list[dict] = list(),
    spreadsheet: Path | str | None = None,
    variable_dicts: list[dict] | None = None,
    model_name: str | None = None,
    require_one_of_images: list[str] = list(),
    exclude_files: Sequence[str | Path] | None = None,
) -> list[ResultDict]:
    results = results.copy()

    data_frame = None
    categorical_dict: dict = dict()
    if spreadsheet is not None:
        spreadsheet = Path(spreadsheet)
        if variable_dicts is not None:
            data_frame = prepare_data_frame(spreadsheet, variable_dicts)
            categorical_dict = get_categorical_dict(data_frame, variable_dicts)

    if len(require_one_of_images) > 0:
        results = [
            result
            for result in results
            if isinstance(result, dict)
            and any(
                key in result.get("images", dict()) for key in require_one_of_images
            )
        ]

    for filter_dict in filter_dicts:
        filter_fun = parse_filter_dict(
            filter_dict,
            categorical_dict,
            data_frame,
            model_name,
        )
        if filter_fun is not None:
            results = list(filter(filter_fun, results))

    if exclude_files is not None:
        decision_maker = QCDecisionMaker(exclude_files)
        results = [
            result
            for result in results
            if decision_maker.get(result["tags"]) is Decision.INCLUDE
        ]

    return results
