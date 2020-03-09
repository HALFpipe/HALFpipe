# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys
from itertools import product

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface
)
import pandas as pd
import numpy as np
from patsy import (
    ModelDesc,
    dmatrix,
    Term,
    LookupFactor
)


def _check_multicollinearity(matrix):
    # taken from CPAC

    sys.stdout.write("Checking for multicollinearity in the model..\n")

    U, s, V = np.linalg.svd(matrix)

    max_singular = np.max(s)
    min_singular = np.min(s)

    sys.stdout.write("max_singular={} min_singular={} rank={}\n".format(
        max_singular, min_singular, np.linalg.matrix_rank(matrix)))

    if min_singular == 0:
        sys.stdout.write("[!] CPAC warns: Detected multicollinearity in the " +
                         "computed group-level analysis model. Please double-"
                         "check your model design.\n\n")


def _group_design(data, subjects):
    covariates_columns = {}
    factor_columns = {}
    for k, v in data.items():
        # only include factors with defined contrasts
        # other factors are for sub-group analyses only
        if "SubjectGroups" in v and "Contrasts" in v:
            factor_columns[k] = v["SubjectGroups"]
        if "Covariate" in v:
            covariates_columns[k] = v["Covariate"]

    # separate
    covariates = pd.DataFrame.from_dict(covariates_columns, orient="columns")
    factors = pd.DataFrame.from_dict(factor_columns, orient="columns")

    # only keep subjects that are in this analysis
    # also sets order
    covariates = covariates.loc[subjects, :]
    factors = factors.loc[subjects, :]

    # Demean covariates for flameo
    covariates -= covariates.mean()

    # replace np.nan by 0 for demeaned_covariates file and regression models
    covariates = covariates.replace({np.nan: 0})

    # change type first to string then to category
    factors = factors.astype(str)
    factors = factors.astype("category")

    # merge
    dataframe = factors.join(covariates, how="outer").loc[subjects, :]

    # remove zero variance columns
    columns_var_gt_0 = dataframe.apply(pd.Series.nunique) > 1
    dataframe = dataframe.loc[:, columns_var_gt_0]

    # don't need to specify lhs
    lhs = []

    # specify patsy design matrix
    rhs = ([Term([])] +  # force intercept
           [Term([LookupFactor(name)]) for name in dataframe])
    modelDesc = ModelDesc(lhs, rhs)
    dmat = dmatrix(modelDesc, dataframe, return_type="dataframe")
    _check_multicollinearity(dmat)

    # prepare lsmeans
    uniqueValuesForFactors = [
        (0.0,)
        if pd.api.types.is_numeric_dtype(dataframe[f].dtype) else
        dataframe[f].unique()
        for f in dataframe.columns
    ]
    grid = pd.DataFrame(list(product(*uniqueValuesForFactors)),
                        columns=dataframe.columns)
    refDmat = dmatrix(dmat.design_info, grid, return_type="dataframe")

    # data frame to store contrasts
    contrastVectors = pd.DataFrame(columns=dmat.columns)

    # create intercept contrast separately
    contrastIntercept = refDmat.mean()
    contrastVectors.loc["mean", :] = \
        contrastIntercept

    for field in dataframe.columns:
        _data = data[field]
        if "Contrasts" in _data:
            if "SubjectGroups" in _data:
                contrasts = _data["Contrasts"]
                fieldLevels = dataframe[field].unique()
                # Generate the lsmeans matrix where there is one row for each
                # factor level. Each row is a contrast vector.
                # This contrast vector corresponds to the mean of the dependent
                # variable at the factor level.
                # For example, we would have one row that calculates the mean
                # for patients, and one for controls.
                lsmeans = pd.DataFrame(index=fieldLevels, columns=dmat.columns)
                for level in fieldLevels:
                    lsmeans.loc[level, :] = \
                        refDmat.loc[grid[field] == level, :].mean()
                for contrastName, valueDict in contrasts.items():
                    names = [name
                             for name in valueDict.keys()
                             if name in fieldLevels]
                    values = [valueDict[name] for name in names]
                    # If we wish to test the mean of each group against zero,
                    # we can simply use these contrasts and be done.
                    # To test a linear hypothesis such as patient-control=0,
                    # which is expressed here as {"patient":1, "control":-1},
                    # we translate it to a contrast vector by taking the linear
                    # combination of the lsmeans contrasts.
                    contrastVector = \
                        lsmeans.loc[names, :].mul(values, axis=0).sum()
                    contrastVectors.loc[contrastName, :] = contrastVector
        if "Covariate" in _data:
            contrastIntercept = dmat.design_info.linear_constraint(
                {field: 0})
            contrastVectors.loc[field, contrastIntercept.variable_names] = \
                contrastIntercept.coefs.ravel()

    npts, nevs = dmat.shape

    if nevs >= npts:
        sys.stdout.write("No design generated. nevs >= npts\n")
        return ({"intercept": [1.0 for s in subjects]},
                [["mean", "T", ["intercept"], [1]]], ["mean"])

    regressors = {
        d: dmat[d].tolist() for d in dmat.columns
    }
    contrasts = [
        [contrastName, "T", contrastVectors.columns.tolist(), coefs.tolist()]
        for contrastName, coefs in contrastVectors.iterrows()]
    contrast_names = [c[0] for c in contrasts]

    return regressors, contrasts, contrast_names


class GroupDesignInputSpec(TraitedSpec):
    data = traits.Dict(desc="group data")
    subjects = traits.List(traits.Str, desc="subject list")


class GroupDesignOutputSpec(TraitedSpec):
    regressors = traits.Any()
    contrasts = traits.Any()
    contrast_names = traits.List(traits.Str, desc="contrast names list")


class GroupDesign(SimpleInterface):
    """ interface to construct a group design """
    input_spec = GroupDesignInputSpec
    output_spec = GroupDesignOutputSpec

    def _run_interface(self, runtime):
        regressors, contrasts, contrast_names = _group_design(
            data=self.inputs.data,
            subjects=self.inputs.subjects,
        )
        self._results["regressors"] = regressors
        self._results["contrasts"] = contrasts
        self._results["contrast_names"] = contrast_names

        return runtime
