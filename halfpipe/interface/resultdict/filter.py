# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Callable, Dict, List, Optional

from glob import glob
import logging
from math import isclose

import numpy as np
import pandas as pd
from marshmallow import ValidationError

from .base import ResultdictsOutputSpec

from ...schema.result import MeanStd
from ...io.index import ExcludeDatabase
from ...io.parse import loadspreadsheet
from ...model.tags import entities, entity_longnames
from ...utils import inflect_engine

from nipype.interfaces.base import (
    traits,
    BaseInterfaceInputSpec,
    SimpleInterface,
    isdefined,
    File
)

logger = logging.getLogger("halfpipe")


def _get_data_frame(file_path, variable_dicts):
    data_frame = loadspreadsheet(file_path, dtype=object)

    id_column = None
    for variable_dict in variable_dicts:
        if variable_dict.get("type") == "id":
            id_column = variable_dict.get("name")
            break

    if id_column is None:
        raise ValueError(f'Column "{id_column}" not found')

    data_frame[id_column] = pd.Series(data_frame[id_column], dtype=str)  # type: ignore
    if all(str(id).startswith("sub-") for id in data_frame[id_column]):  # for bids
        data_frame[id_column] = [str(id).replace("sub-", "") for id in data_frame[id_column]]
    data_frame = data_frame.set_index(id_column)

    return data_frame


def _get_categorical_dict(data_frame, variable_dicts):
    categorical_columns = []
    for variable_dict in variable_dicts:
        if variable_dict.get("type") == "categorical":
            categorical_columns.append(variable_dict.get("name"))

    categorical_data_frame = data_frame[categorical_columns].astype(str)
    return categorical_data_frame.to_dict()


def _format_tags(tagdict):
    tagdesc_list = []

    for entity in entities:
        tagval = tagdict.get(entity)

        if tagval is None:
            continue

        if entity in entity_longnames:
            entity = entity_longnames[entity]

        tagdesc_list.append(f'{entity} "{tagval}"')

    return ", ".join(tagdesc_list)


def _make_group_filterfun(filter_dict: Dict, categorical_dict: Dict, model_desc: str) -> Optional[Callable[[Dict], bool]]:
    variable = filter_dict.get("variable")
    if variable not in categorical_dict:
        return None

    levels = filter_dict.get("levels")
    if levels is None or len(levels) == 0:
        return None

    variable_dict = categorical_dict[variable]
    selectedsubjects = frozenset(
        subject for subject, value in variable_dict.items() if value in levels
    )

    levelsdesc = inflect_engine.join([f'"{v}"' for v in levels], conj="or")

    action = filter_dict["action"]

    if action == "include":
        def group_include_filterfun(d):
            sub = d.get("tags").get("sub")
            res = sub in selectedsubjects

            if res is False:
                logger.info(f'Excluding subject "{sub}" {model_desc}because "{variable}" is not {levelsdesc}')

            return res

        return group_include_filterfun

    elif action == "exclude":
        def group_exclude_filterfun(d):
            sub = d["tags"].get("sub")
            res = sub not in selectedsubjects

            if res is False:
                logger.info(f'Excluding subject "{sub}" {model_desc}because "{variable}" is {levelsdesc}')

            return res

        return group_exclude_filterfun

    else:
        raise ValueError(f'Invalid action "{action}"')


def _make_missing_filterfun(filter_dict: Dict, data_frame: pd.DataFrame, model_desc: str) -> Optional[Callable[[Dict], bool]]:
    variable = filter_dict["variable"]
    if variable not in data_frame.columns:
        return None

    assert filter_dict["action"] == "exclude"

    isfinite = pd.notnull(data_frame[variable])  # type: ignore

    selectedsubjects = frozenset(isfinite.index[isfinite])

    def missing_filterfun(d):
        sub = d["tags"].get("sub")
        res = sub in selectedsubjects

        if res is False:
            logger.warning(f'Excluding subject "{sub}" {model_desc}because "{variable}" is missing')

        return res

    return missing_filterfun


def _make_cutoff_filterfun(filter_dict: Dict, model_desc: str) -> Optional[Callable[[Dict], bool]]:
    assert filter_dict["action"] == "exclude"

    cutoff = filter_dict["cutoff"]
    if cutoff is None or not isinstance(cutoff, float):
        raise ValueError(f'Invalid cutoff "{cutoff}"')

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
            try:
                mean_std = MeanStd.Schema().load(val)
                assert isinstance(mean_std, MeanStd)
                x = mean_std.mean
            except (ValidationError, AssertionError) as e:
                raise ValueError(f'Cannot filter by "{val}"') from e

        res = x <= cutoff

        if res is False:
            tags = d["tags"]
            logger.warning(
                f'Excluding ({_format_tags(tags)}) {model_desc}'
                f'because "{filter_field}" is larger than {cutoff:f}'
            )

        return res

    return cutoff_filterfun


def _parse_filter_dict(
    filter_dict: Dict,
    categorical_dict: Dict = dict(),
    data_frame: Optional[pd.DataFrame] = None,
    model_name: Optional[str] = None
) -> Optional[Callable[[Dict], bool]]:
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
    exclude_files = traits.Str()


class FilterResultdicts(SimpleInterface):
    input_spec = FilterResultdictsInputSpec
    output_spec = ResultdictsOutputSpec

    def _run_interface(self, runtime):
        out_dicts: List[Dict[str, Dict]] = self.inputs.in_dicts.copy()

        data_frame = None
        categorical_dict = None
        if isdefined(self.inputs.spreadsheet) and isdefined(self.inputs.variable_dicts):
            data_frame = _get_data_frame(self.inputs.spreadsheet, self.inputs.variable_dicts)
            categorical_dict = _get_categorical_dict(data_frame, self.inputs.variable_dicts)

        model_name = None
        if isdefined(self.inputs.model_name):
            model_name = self.inputs.model_name

        filter_dicts: List[Dict] = list()
        if isdefined(self.inputs.filter_dicts):
            filter_dicts.extend(self.inputs.filter_dicts)

        kwargs = dict(
            data_frame=data_frame,
            categorical_dict=categorical_dict,
            model_name=model_name
        )

        if isdefined(self.inputs.require_one_of_images):
            require_one_of_images = self.inputs.require_one_of_images
            if len(require_one_of_images) > 0:
                out_dicts = [
                    out_dict
                    for out_dict in out_dicts
                    if isinstance(out_dict, dict)
                    and any(
                        key in out_dict.get("images")
                        for key in require_one_of_images
                    )
                ]
        for filter_dict in filter_dicts:
            filter_fun = _parse_filter_dict(filter_dict, **kwargs)
            if filter_fun is not None:
                out_dicts = list(filter(filter_fun, out_dicts))

        if isdefined(self.inputs.exclude_files):
            exclude_files = glob(self.inputs.exclude_files)
            exclude_files = tuple(sorted(exclude_files))  # make hashable
            database = ExcludeDatabase.cached(exclude_files)
            out_dicts = [
                out_dict for out_dict in out_dicts if database.get(**out_dict["tags"]) is False
            ]

        self._results["resultdicts"] = out_dicts

        return runtime
