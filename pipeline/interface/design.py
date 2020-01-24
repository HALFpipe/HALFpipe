# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import sys

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
    columns = {}
    for k, v in data.items():
        # only include factors with defined contrasts
        # other factors are for sub-group analyses only
        if "SubjectGroups" in v and "Contrasts" in v:
            columns[k] = v["SubjectGroups"]
        if "Covariate" in v:
            columns[k] = v["Covariate"]

    dataframe = pd.DataFrame(columns)

    # only keep subjects that are in this analysis
    # also sets order
    dataframe = dataframe.loc[subjects, :]

    # remove zero variance columns
    columns_var_gt_0 = (dataframe != dataframe.iloc[0]).any()
    dataframe = dataframe.loc[:, columns_var_gt_0]

    # separate
    covariates = dataframe.select_dtypes(include=np.number)
    factors = dataframe.select_dtypes(exclude=np.number)

    # replace not available values by numpy NaN to be ignored for demeaning
    covariates = covariates.replace({
        "NaN": np.nan, "n/a": np.nan, "NA": np.nan
    })

    # Demean covariates for flameo
    covariates -= covariates.mean()

    # replace np.nan by 0 for demeaned_covariates file and regression models
    covariates = covariates.replace({np.nan: 0})

    factors = factors.astype("category")

    dataframe = pd.concat((factors, covariates), axis=1)

    # with intercept
    desc = ModelDesc([], [Term([])] + [
        Term([LookupFactor(name)]) for name in dataframe
    ])

    dmatrix_obj = dmatrix(desc, dataframe, return_type="dataframe")

    contrast_dict = {}

    lc = dmatrix_obj.design_info.linear_constraint({"Intercept": 0})
    contrast_dict["Intercept"] = lc

    for c in covariates:
        if data[c]["Contrasts"]:
            lc = dmatrix_obj.design_info.linear_constraint({c: 0})
            contrast_dict[c] = lc

    regressors = {
        k: dmatrix_obj.loc[:, k].tolist() for k in dmatrix_obj
    }
    contrasts = [[k, "T", lc.variable_names, lc.coefs]
                 for k, lc in contrast_dict.items()]
    contrast_names = [c[0] for c in contrasts]

    return regressors, contrasts, contrast_names


class GroupDesignInputSpec(TraitedSpec):
    data = traits.Dict(desc="group data")
    subjects = traits.List(traits.Str, desc="subject list")


class GroupDesignOutputSpec(TraitedSpec):
    regressors = traits.Any()
    contrasts = traits.Any()
    contrast_names = traits.Str()


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

# # transform into dict to extract regressors for level2model
# covariates = df_covariates.to_dict()
#
# # transform to dictionary of lists
# regressors = {k: [float(v[s]) for s in subjects] for k, v in covariates.items()}
#
# if (subject_groups is None) or (bool(subject_groups) is False):
#     # one-sample t-test with covariates
#     regressors["intercept"] = [1.0 for s in subjects]
#     level2model = pe.Node(
#         interface=fsl.MultipleRegressDesign(
#             regressors=regressors,
#             contrasts=contrasts
#         ),
#         name="l2model"
#     )
# else:
#     # two-sample t-tests with covariates
#
#     # dummy coding of variables: group names --> numbers in the matrix
#     # see fsl feat documentation
#     # https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FEAT/UserGuide#Tripled_Two-Group_Difference_.28.22Tripled.22_T-Test.29
#     dummies = pd.Series(subject_groups).str.get_dummies().to_dict()
#     # transform to dictionary of lists
#     dummies = {k: [float(v[s]) for s in subjects] for k, v in dummies.items()}
#     regressors.update(dummies)
