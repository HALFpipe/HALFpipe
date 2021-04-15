# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from glob import glob
import logging

import numpy as np
import pandas as pd

from .base import ResultdictsOutputSpec
from ...io.index import ExcludeDatabase
from ...io.parse import loadspreadsheet
from ...model.resultdict import ResultdictSchema
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


def _aggregate_if_needed(inval):
    if isinstance(inval, (list, tuple)):
        return np.asarray(inval).mean()
    return float(inval)


def _get_dataframe(filepath, variabledicts):
    dataframe = loadspreadsheet(filepath, dtype=object)

    for variabledict in variabledicts:
        if variabledict.get("type") == "id":
            id_column = variabledict.get("name")
            break

    dataframe[id_column] = pd.Series(dataframe[id_column], dtype=str)
    if all(str(id).startswith("sub-") for id in dataframe[id_column]):  # for bids
        dataframe[id_column] = [str(id).replace("sub-", "") for id in dataframe[id_column]]
    dataframe = dataframe.set_index(id_column)

    return dataframe


def _get_categorical_dict(dataframe, variabledicts):
    categorical_columns = []
    for variabledict in variabledicts:
        if variabledict.get("type") == "categorical":
            categorical_columns.append(variabledict.get("name"))

    categorical_dataframe = dataframe[categorical_columns].astype(str)
    return categorical_dataframe.to_dict()


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


def _parse_filterdict(filterdict, **kwargs):
    action = filterdict.get("action")

    categorical_dict = kwargs.get("categorical_dict")
    dataframe = kwargs.get("dataframe")
    modelname = kwargs.get("modelname")

    modeldesc = ""
    if modelname is not None:
        modeldesc = f'from model "{modelname}" '

    filtertype = filterdict.get("type")
    if filtertype == "group":
        variable = filterdict.get("variable")
        if variable not in categorical_dict:
            return

        levels = filterdict.get("levels")
        if levels is None or len(levels) == 0:
            return

        variable_dict = categorical_dict[variable]
        selectedsubjects = frozenset(
            subject for subject, value in variable_dict.items() if value in levels
        )

        levelsdesc = inflect_engine.join([f'"{v}"' for v in levels], conj="or")

        if action == "include":
            def group_filterfun(d):
                sub = d.get("tags").get("sub")
                res = sub in selectedsubjects

                if res is False:
                    logger.info(f'Excluding subject "{sub}" {modeldesc}because "{variable}" is not {levelsdesc}')

                return res

            return group_filterfun

        elif action == "exclude":
            def group_filterfun(d):
                sub = d["tags"].get("sub")
                res = sub not in selectedsubjects

                if res is False:
                    logger.info(f'Excluding subject "{sub}" {modeldesc}because "{variable}" is {levelsdesc}')

                return res

            return group_filterfun

        else:
            raise ValueError(f'Invalid action "{action}"')

    elif filtertype == "missing":

        assert dataframe is not None

        variable = filterdict.get("variable")
        if variable not in dataframe.columns:
            return

        assert action == "exclude"

        isfinite = pd.notnull(dataframe[variable])

        selectedsubjects = frozenset(isfinite.index[isfinite])

        def missing_filterfun(d):
            sub = d["tags"].get("sub")
            res = sub in selectedsubjects

            if res is False:
                logger.warning(f'Excluding subject "{sub}" {modeldesc}because "{variable}" is missing')

            return res

        return missing_filterfun

    elif filtertype == "cutoff":

        assert action == "exclude"

        cutoff = filterdict["cutoff"]
        if cutoff is None or not isinstance(cutoff, float):
            raise ValueError(f'Invalid cutoff "{cutoff}"')

        filterfield = filterdict["field"]

        def cutoff_filterfun(d):
            val = _aggregate_if_needed(d["vals"].get(filterfield, np.inf))
            res = val <= cutoff

            if res is False:
                tags = d["tags"]
                logger.warning(
                    f'Excluding ({_format_tags(tags)}) {modeldesc}'
                    f'because "{filterfield}" is larger than {cutoff:f}'
                )

            return res

        return cutoff_filterfun


class FilterResultdictsInputSpec(BaseInterfaceInputSpec):
    indicts = traits.List(traits.Dict(traits.Str(), traits.Any()), mandatory=True)
    modelname = traits.Str()
    filterdicts = traits.List(traits.Any(), desc="filter list")
    variabledicts = traits.List(traits.Any(), desc="variable list")
    spreadsheet = File(desc="spreadsheet", exists=True)
    requireoneofimages = traits.List(
        traits.Str(), desc="only keep resultdicts that have at least one of these keys"
    )
    excludefiles = traits.Str()


class FilterResultdicts(SimpleInterface):
    input_spec = FilterResultdictsInputSpec
    output_spec = ResultdictsOutputSpec

    def _run_interface(self, runtime):
        outdicts = self.inputs.indicts.copy()

        resultdict_schema = ResultdictSchema()
        outdicts = [resultdict_schema.load(outdict) for outdict in outdicts]  # validate

        dataframe = None
        categorical_dict = None
        if isdefined(self.inputs.spreadsheet) and isdefined(self.inputs.variabledicts):
            dataframe = _get_dataframe(self.inputs.spreadsheet, self.inputs.variabledicts)
            categorical_dict = _get_categorical_dict(dataframe, self.inputs.variabledicts)

        modelname = self.inputs.modelname
        if not isdefined(modelname):
            modelname = None

        filterdicts = []
        if isdefined(self.inputs.filterdicts):
            filterdicts = self.inputs.filterdicts

        kwargs = dict(
            dataframe=dataframe,
            categorical_dict=categorical_dict,
            modelname=modelname
        )

        for filterdict in filterdicts:
            filterfun = _parse_filterdict(filterdict, **kwargs)
            if filterfun is not None:
                outdicts = filter(filterfun, outdicts)

        if isdefined(self.inputs.requireoneofimages):
            requireoneofimages = self.inputs.requireoneofimages
            if len(requireoneofimages) > 0:
                outdicts = [
                    outdict
                    for outdict in outdicts
                    if any(
                        requireoneofkey in outdict.get("images")
                        for requireoneofkey in requireoneofimages
                    )
                ]

        if isdefined(self.inputs.excludefiles):
            excludefiles = glob(self.inputs.excludefiles)
            excludefiles = tuple(sorted(excludefiles))  # make hashable
            database = ExcludeDatabase.cached(excludefiles)
            outdicts = [
                outdict for outdict in outdicts if database.get(**outdict.get("tags")) is False
            ]

        self._results["resultdicts"] = outdicts

        return runtime
