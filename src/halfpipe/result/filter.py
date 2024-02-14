# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

from ..design import prepare_data_frame
from ..exclude import Decision, QCDecisionMaker
from ..logging import logger
from ..utils.format import format_tags, inflect_engine, normalize_subject
from .base import ResultDict
from .variables import Continuous


def get_categorical_dict(
    data_frame: pd.DataFrame,
    variable_dicts: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    categorical_columns = []
    for variable_dict in variable_dicts:
        if variable_dict.get("type") == "categorical":
            categorical_columns.append(variable_dict.get("name"))

    data_frame = data_frame[categorical_columns].astype(str)
    data_frame_dict = data_frame.to_dict()

    categorical_dict: dict[str, dict[str, str]] = dict()
    for key, value in data_frame_dict.items():
        if not isinstance(key, str):
            raise ValueError("Categorical variable names must be strings")
        categorical_dict[key] = value

    return categorical_dict


def make_group_filter(
    filter_dict: dict[str, Any],
    categorical_dict: dict[str, dict[str, str]],
    model_desc: str,
) -> Callable[[dict], bool] | None:
    variable = filter_dict.get("variable")
    if not isinstance(variable, str):
        return None
    if variable not in categorical_dict:
        return None

    levels = filter_dict.get("levels")
    if levels is None or len(levels) == 0:
        return None

    variable_dict = categorical_dict[variable]
    selected_subjects = frozenset(normalize_subject(subject) for subject, value in variable_dict.items() if value in levels)

    levelsdesc = inflect_engine.join([f'"{v}"' for v in levels], conj="or")

    action = filter_dict["action"]

    if action == "include":

        def group_include_filter(d):
            subject = d.get("tags").get("sub")
            subject = normalize_subject(subject)

            res = subject in selected_subjects

            if res is False:
                logger.info(f'Excluding subject "{subject}" {model_desc}because "{variable}" is not {levelsdesc}')

            return res

        return group_include_filter

    elif action == "exclude":

        def group_exclude_filter(d):
            subject = d["tags"].get("sub")
            subject = normalize_subject(subject)

            res = subject not in selected_subjects

            if res is False:
                logger.info(f'Excluding subject "{subject}" {model_desc}because "{variable}" is {levelsdesc}')

            return res

        return group_exclude_filter

    else:
        raise ValueError(f'Invalid action "{action}"')


def make_missing_filter(filter_dict: dict, data_frame: pd.DataFrame, model_desc: str) -> Callable[[dict], bool] | None:
    variable = filter_dict["variable"]
    if variable not in data_frame.columns:
        return None

    assert filter_dict["action"] == "exclude"

    is_finite = pd.notnull(data_frame[variable])
    assert isinstance(is_finite, pd.Series)

    selected_subjects = frozenset(map(normalize_subject, is_finite.index[is_finite]))

    def missing_filter(d):
        subject = d["tags"].get("sub")
        subject = normalize_subject(subject)

        res = subject in selected_subjects

        if res is False:
            logger.warning(f'Excluding subject "{subject}" {model_desc}because "{variable}" is missing')

        return res

    return missing_filter


def make_cutoff_filter(filter_dict: dict, model_desc: str) -> Callable[[dict], bool] | None:
    assert filter_dict["action"] == "exclude"

    cutoff = filter_dict["cutoff"]
    assert isinstance(cutoff, float)

    filter_field = filter_dict["field"]

    if filter_field == "fd_perc" and cutoff < 1 and not isclose(cutoff, 1):
        logger.warning(f'The cutoff for "fd_perc" of {cutoff:f} was re-scaled to {cutoff * 100} percent')
        cutoff *= 100

    def cutoff_filter(d: dict) -> bool:
        tags = d["tags"]

        if "task" not in tags:
            logger.info(f"Skipping cutoff filter for structural ({format_tags(tags)})")
            return True

        vals = d.get("vals")
        if vals is None:
            logger.warning(f"Excluding ({format_tags(tags)}) {model_desc}" f'because "{filter_field}" is missing. ')
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
            logger.info(f"Excluding ({format_tags(tags)}) {model_desc}" f'because "{filter_field}" is larger than {cutoff:f}')

        return res

    return cutoff_filter


def parse_filter_dict(
    filter_dict: dict,
    categorical_dict: dict[str, dict[str, str]] | None = None,
    data_frame: pd.DataFrame | None = None,
    model_name: str | None = None,
) -> Callable[[dict], bool] | None:
    categorical_dict = dict() if categorical_dict is None else categorical_dict
    model_desc = ""
    if model_name is not None:
        model_desc = f'from model "{model_name}" '

    filter_type = filter_dict.get("type")
    if filter_type == "group":
        return make_group_filter(filter_dict, categorical_dict, model_desc)

    elif filter_type == "missing":
        if data_frame is None:
            raise ValueError("Missing data_frame")
        return make_missing_filter(filter_dict, data_frame, model_desc)

    elif filter_type == "cutoff":
        return make_cutoff_filter(filter_dict, model_desc)

    return None


def filter_results(
    results: list[ResultDict],
    filter_dicts: list[dict] | None = None,
    spreadsheet: Path | str | pd.DataFrame | None = None,
    variable_dicts: list[dict] | None = None,
    model_name: str | None = None,
    require_one_of_images: list[str] | None = None,
    exclude_files: Sequence[str | Path] | None = None,
) -> list[ResultDict]:
    results = results.copy()
    filter_dicts = list() if filter_dicts is None else filter_dicts
    require_one_of_images = list() if require_one_of_images is None else require_one_of_images

    categorical_dict: dict[str, dict[str, str]] = dict()
    data_frame: pd.DataFrame | None = None
    if variable_dicts is not None:
        if isinstance(spreadsheet, pd.DataFrame):
            data_frame = spreadsheet
        elif spreadsheet is not None:
            spreadsheet = Path(spreadsheet)
            data_frame = prepare_data_frame(spreadsheet, variable_dicts)
        if data_frame is not None:
            categorical_dict = get_categorical_dict(data_frame, variable_dicts)

    if len(require_one_of_images) > 0:
        results = [
            result
            for result in results
            if isinstance(result, dict) and any(key in result.get("images", dict()) for key in require_one_of_images)
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
        exclude_paths = list(map(Path, exclude_files))
        decision_maker = QCDecisionMaker(exclude_paths)
        results = [result for result in results if decision_maker.get(result["tags"]) is Decision.INCLUDE]

    return results
