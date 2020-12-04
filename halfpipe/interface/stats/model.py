# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from itertools import product
from collections import OrderedDict

import logging

from nipype.interfaces.base import traits, TraitedSpec, SimpleInterface, File
import pandas as pd
import numpy as np
from patsy import ModelDesc, dmatrix, Term, LookupFactor

from ...io import loadspreadsheet

logger = logging.getLogger("halfpipe")


def _check_multicollinearity(matrix):
    # taken from C-PAC

    logging.getLogger("halfpipe").info("Checking for multicollinearity in the model..")

    U, s, V = np.linalg.svd(matrix)

    max_singular = np.max(s)
    min_singular = np.min(s)

    logger.info(
        f"max_singular={max_singular} min_singular={min_singular} "
        f"rank={np.linalg.matrix_rank(matrix)}"
    )

    if min_singular == 0:
        logger.warning(
            "[!] halfpipe warns: Detected multicollinearity in the "
            + "computed group-level analysis model. Please double-"
            "check your model design."
        )


def _group_model(spreadsheet=None, contrastdicts=None, variabledicts=None, subjects=None):
    rawdataframe = loadspreadsheet(spreadsheet, dtype=object)

    id_column = None
    for variabledict in variabledicts:
        if variabledict["type"] == "id":
            id_column = variabledict["name"]
            break

    assert id_column is not None, "Missing id column, cannot specify model"

    rawdataframe[id_column] = pd.Series(rawdataframe[id_column], dtype=str)
    if all(str(id).startswith("sub-") for id in rawdataframe[id_column]):  # for bids
        rawdataframe[id_column] = [str(id).replace("sub-", "") for id in rawdataframe[id_column]]
    rawdataframe = rawdataframe.set_index(id_column)

    continuous_columns = []
    categorical_columns = []
    columns_in_order = []
    for variabledict in variabledicts:
        if variabledict["type"] == "continuous":
            continuous_columns.append(variabledict["name"])
            columns_in_order.append(variabledict["name"])
        elif variabledict["type"] == "categorical":
            categorical_columns.append(variabledict["name"])
            columns_in_order.append(variabledict["name"])

    # separate
    continuous = rawdataframe[continuous_columns]
    categorical = rawdataframe[categorical_columns]

    # only keep subjects that are in this analysis
    # also sets order
    continuous = continuous.loc[subjects, :]
    categorical = categorical.loc[subjects, :]

    # change type to numeric
    continuous = continuous.astype(np.float64)

    # Demean continuous for flameo
    continuous -= continuous.mean()

    # replace np.nan by 0 for demeaned_continuous file and regression models
    continuous = continuous.replace({np.nan: 0})

    # change type first to string then to category
    categorical = categorical.astype(str)
    categorical = categorical.astype("category")

    # merge
    dataframe = categorical.join(continuous, how="outer").loc[subjects, :]

    # maintain order
    dataframe = dataframe[columns_in_order]

    # remove zero variance columns
    columns_var_gt_0 = dataframe.apply(pd.Series.nunique) > 1
    dataframe = dataframe.loc[:, columns_var_gt_0]

    # don't need to specify lhs
    lhs = []

    # generate rhs
    rhs = [Term([])]  # force intercept
    for contrastdict in contrastdicts:
        if contrastdict["type"] == "infer":
            # for every term in the model a contrast of type infer needs to be specified
            rhs.append(Term([LookupFactor(name) for name in contrastdict["variable"]]))

    # specify patsy design matrix
    modelDesc = ModelDesc(lhs, rhs)
    dmat = dmatrix(modelDesc, dataframe, return_type="dataframe")
    _check_multicollinearity(dmat)

    # prepare lsmeans
    uniqueValuesForCategorical = [
        (0.0,) if pd.api.types.is_numeric_dtype(dataframe[f].dtype) else dataframe[f].unique()
        for f in dataframe.columns
    ]
    grid = pd.DataFrame(list(product(*uniqueValuesForCategorical)), columns=dataframe.columns)
    refDmat = dmatrix(dmat.design_info, grid, return_type="dataframe")

    # data frame to store contrasts
    contrastMats = []

    for field, columnslice in dmat.design_info.term_name_slices.items():
        constraint = {column: 0 for column in dmat.design_info.column_names[columnslice]}
        contrast = dmat.design_info.linear_constraint(constraint)
        assert np.all(contrast.variable_names == dmat.columns)
        contrastMat = pd.DataFrame(contrast.coefs, columns=dmat.columns)
        contrastMats.append((field, contrastMat))

    for contrastdict in contrastdicts:
        if contrastdict["type"] == "t":
            (variable,) = contrastdict["variable"]
            variableLevels = dataframe[variable].unique()
            # Generate the lsmeans matrix where there is one row for each
            # factor level. Each row is a contrast vector.
            # This contrast vector corresponds to the mean of the dependent
            # variable at the factor level.
            # For example, we would have one row that calculates the mean
            # for patients, and one for controls.
            lsmeans = pd.DataFrame(index=variableLevels, columns=dmat.columns)
            for level in variableLevels:
                lsmeans.loc[level, :] = refDmat.loc[grid[variable] == level, :].mean()
            valueDict = contrastdict["values"]
            names = [name for name in valueDict.keys() if name in variableLevels]
            values = [valueDict[name] for name in names]
            # If we wish to test the mean of each group against zero,
            # we can simply use these contrasts and be done.
            # To test a linear hypothesis such as patient-control=0,
            # which is expressed here as {"patient":1, "control":-1},
            # we translate it to a contrast vector by taking the linear
            # combination of the lsmeans contrasts.
            contrastVector = lsmeans.loc[names, :].mul(values, axis=0).sum()
            contrastMat = pd.DataFrame([contrastVector], columns=dmat.columns)
            contrastMats.append((contrastdict["name"], contrastMat))

    npts, nevs = dmat.shape

    if nevs >= npts:
        logger.warning(
            "Reverting to simple intercept only design. \n"
            f"nevs ({nevs}) >= npts ({npts})"
        )
        return (
            {"intercept": [1.0] * len(subjects)},
            [["mean", "T", ["Intercept"], [1]]],
            ["mean"],
        )

    regressors = dmat.to_dict(orient="list", into=OrderedDict)

    contrasts = []
    contrast_names = []

    for contrastName, contrastMat in contrastMats:  # t contrasts
        if contrastMat.shape[0] == 1:
            contrastVec = contrastMat.squeeze()
            contrasts.append((contrastName, "T", list(contrastVec.keys()), list(contrastVec)))

            contrast_names.append(contrastName)

    for contrastName, contrastMat in contrastMats:  # f contrasts
        if contrastMat.shape[0] > 1:

            tcontrasts = []  # an f contrast consists of multiple t contrasts
            for i, contrastVec in contrastMat.iterrows():
                tname = f"{contrastName}_{i:d}"
                tcontrasts.append((tname, "T", list(contrastVec.keys()), list(contrastVec)))

            contrasts.extend(tcontrasts)  # add t contrasts to the model
            contrasts.append((contrastName, "F", tcontrasts))  # then add the f contrast

            contrast_names.append(contrastName)  # we only care about the f contrast

    return regressors, contrasts, contrast_names


class LinearModelInputSpec(TraitedSpec):
    spreadsheet = File(exist=True, mandatory=True)
    contrastdicts = traits.List(
        traits.Dict(traits.Str, traits.Any),
        mandatory=True
    )
    variabledicts = traits.List(
        traits.Dict(traits.Str, traits.Any), mandatory=True
    )
    subjects = traits.List(traits.Str, mandatory=True)


class ModelOutputSpec(TraitedSpec):
    regressors = traits.Dict(traits.Str, traits.Any)
    contrasts = traits.List()
    contrast_names = traits.List(traits.Str())


class LinearModel(SimpleInterface):
    """ interface to construct a group design """

    input_spec = LinearModelInputSpec
    output_spec = ModelOutputSpec

    def _run_interface(self, runtime):
        regressors, contrasts, contrast_names = _group_model(
            spreadsheet=self.inputs.spreadsheet,
            contrastdicts=self.inputs.contrastdicts,
            variabledicts=self.inputs.variabledicts,
            subjects=self.inputs.subjects,
        )
        self._results["regressors"] = regressors
        self._results["contrasts"] = contrasts
        self._results["contrast_names"] = contrast_names

        return runtime


class InterceptOnlyModelInputSpec(TraitedSpec):
    n_copes = traits.Range(low=1, desc="number of inputs")


class InterceptOnlyModel(SimpleInterface):
    """ interface to construct a group design """

    input_spec = InterceptOnlyModelInputSpec
    output_spec = ModelOutputSpec

    def _run_interface(self, runtime):
        self._results["regressors"] = {"Intercept": [1.0] * self.inputs.n_copes}
        self._results["contrasts"] = [["Intercept", "T", ["Intercept"], [1]]]
        self._results["contrast_names"] = ["Intercept"]

        return runtime
