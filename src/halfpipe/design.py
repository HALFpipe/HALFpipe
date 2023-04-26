# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict
from itertools import product
from pathlib import Path
from typing import Literal, NamedTuple

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from patsy.desc import (  # separate imports as to not confuse type checker
    ModelDesc,
    Term,
)
from patsy.highlevel import dmatrix
from patsy.user_util import LookupFactor

from .ingest.design import parse_design
from .ingest.spreadsheet import read_spreadsheet
from .logging import logger


def _check_multicollinearity(matrix):
    """
    Adapted from C-PAC
    """

    logger.info("Checking for multicollinearity in the model..")

    _, s, _ = np.linalg.svd(matrix)
    max_singular = np.max(s)
    min_singular = np.min(s)

    rank = np.linalg.matrix_rank(matrix)

    logger.info(
        f"max_singular={max_singular} min_singular={min_singular} " f"rank={rank}"
    )

    if min_singular == 0:
        logger.warning(
            "Detected multicollinearity in the computed group-level analysis model."
            + "Please double-check your model design."
        )


def prepare_data_frame(
    spreadsheet: Path,
    variables: list[dict],
    subjects: list[str] | None = None,
    na_action: Literal["impute"] | None = None,
) -> pd.DataFrame:
    data_frame: pd.DataFrame = read_spreadsheet(spreadsheet, dtype=str)

    # set data frame index
    id_column_name: str | None = None
    for variabledict in variables:
        if variabledict["type"] == "id":
            id_column_name = variabledict["name"]
            break
    if id_column_name is None:
        raise ValueError("Missing id column, cannot specify model")

    id_column = pd.Series(data_frame[id_column_name], dtype=str)
    id_column[:] = [  # remove bids prefixes
        str(subject_id).removeprefix("sub-") for subject_id in id_column
    ]
    data_frame[id_column_name] = id_column
    data_frame.set_index(id_column_name, inplace=True)

    # filter data frame
    if subjects is not None:
        # only keep subjects that are in this analysis
        # also sets order
        data_frame = data_frame.loc[subjects, :]

    # apply variable data types
    continuous_columns: list[str] = list()
    categorical_columns: list[str] = list()
    columns_in_order: list[str] = []
    for variabledict in variables:
        name = variabledict["name"]
        if name not in data_frame:
            continue
        column = data_frame[name]
        # Remove leading and trailing whitespace.
        column = column.str.strip()
        if not isinstance(column, pd.Series):
            continue

        if variabledict["type"] == "continuous":
            continuous_columns.append(name)
            columns_in_order.append(name)
            # change type to numeric
            column = column.astype(float, copy=False)
            # impute missing values with mean
            if na_action == "impute":
                column.fillna(column.mean(), inplace=True)

        elif variabledict["type"] == "categorical":
            categorical_columns.append(name)
            columns_in_order.append(name)
            # change type first to string then to category
            column = column.astype(str).astype("category")
            # set unknown levels to missing
            levels = variabledict["levels"]
            column = column.cat.set_categories(new_categories=levels)
            column = column.cat.remove_unused_categories()
            # impute missing values
            if na_action == "impute":
                column.fillna(column.mode()[0], inplace=True)

        data_frame[name] = column

    # ensure order
    data_frame = data_frame.loc[:, columns_in_order]

    return data_frame


def _generate_rhs(contrasts, columns_var_gt_0) -> list[Term]:
    rhs = [Term([])]  # force intercept
    for contrast in contrasts:
        if contrast["type"] == "infer":
            if not columns_var_gt_0[contrast["variable"]].all():
                logger.warning(
                    f'Not adding term "{contrast["variable"]}" to design matrix '
                    "because it has zero variance"
                )
                continue
            # for every term in the model a contrast of type infer needs to be specified
            rhs.append(Term([LookupFactor(name) for name in contrast["variable"]]))

    return rhs


def _make_contrasts_list(contrast_matrices: list[tuple[str, pd.DataFrame]]):
    contrasts: list[tuple] = []
    contrast_names = []

    for contrast_name, contrast_matrix in contrast_matrices:  # t contrasts
        contrast_name = contrast_name.capitalize()

        if contrast_matrix.shape[0] == 1:
            contrast_vector = contrast_matrix.iloc[0]
            contrasts.append(
                (contrast_name, "T", list(contrast_vector.index), list(contrast_vector))
            )

            contrast_names.append(contrast_name)

    for contrast_name, contrast_matrix in contrast_matrices:  # f contrasts
        contrast_name = contrast_name.capitalize()

        if contrast_matrix.shape[0] > 1:

            tcontrasts = []  # an f contrast consists of multiple t contrasts
            for i, contrast_vector in contrast_matrix.iterrows():
                tname = f"{contrast_name}_{i:d}"
                tcontrasts.append(
                    (tname, "T", list(contrast_vector.index), list(contrast_vector))
                )

            contrasts.extend(tcontrasts)  # add t contrasts to the model
            contrasts.append(
                (contrast_name, "F", tcontrasts)
            )  # then add the f contrast

            contrast_names.append(contrast_name)  # we only care about the f contrast

    contrast_numbers = [f"{i:02d}" for i in range(1, len(contrast_names) + 1)]

    return contrasts, contrast_numbers, contrast_names


class Design(NamedTuple):
    regressor_list: dict[str, list[float]]
    contrast_list: list[tuple]
    contrast_numbers: list[str]
    contrast_names: list[str]


def intercept_only_design(
    n: int,
) -> Design:
    return Design(
        {"intercept": [1.0] * n},
        [("intercept", "T", ["intercept"], [1])],
        ["01"],
        ["intercept"],
    )


def group_design(
    spreadsheet: Path,
    contrasts: list[dict],
    variables: list[dict],
    subjects: list[str],
) -> Design:

    dataframe = prepare_data_frame(spreadsheet, variables, subjects, na_action="impute")

    # remove zero variance columns
    columns_var_gt_0 = dataframe.apply(pd.Series.nunique) > 1  # does not count NA
    assert isinstance(columns_var_gt_0, pd.Series)
    dataframe = dataframe.loc[:, columns_var_gt_0]

    # don't need to specify lhs
    lhs: list[Term] = []

    # generate rhs
    rhs = _generate_rhs(contrasts, columns_var_gt_0)

    # specify patsy design matrix
    model_desc = ModelDesc(lhs, rhs)
    dmat = dmatrix(model_desc, dataframe, return_type="dataframe", NA_action="raise")
    assert isinstance(dmat, pd.DataFrame)
    _check_multicollinearity(dmat)

    # prepare lsmeans
    unique_values_categorical = [
        (0.0,) if is_numeric_dtype(dataframe[f]) else dataframe[f].unique()
        for f in dataframe.columns
    ]
    grid = pd.DataFrame(
        list(product(*unique_values_categorical)), columns=dataframe.columns
    )
    reference_dmat = dmatrix(dmat.design_info, grid, return_type="dataframe")
    assert isinstance(reference_dmat, pd.DataFrame)

    # data frame to store contrasts
    contrast_matrices: list[tuple[str, pd.DataFrame]] = []

    for field, columnslice in dmat.design_info.term_name_slices.items():
        constraint = {
            column: 0 for column in dmat.design_info.column_names[columnslice]
        }
        contrast = dmat.design_info.linear_constraint(constraint)

        assert np.all(contrast.variable_names == dmat.columns)

        contrast_matrix = pd.DataFrame(contrast.coefs, columns=dmat.columns)

        if field == "Intercept":  # do not capitalize
            field = field.lower()
        contrast_matrices.append((field, contrast_matrix))

    for contrast in contrasts:
        if contrast["type"] == "t":
            (variable,) = contrast["variable"]
            variable_levels: list[str] = list(dataframe[variable].unique())

            # Generate the lsmeans matrix where there is one row for each
            # factor level. Each row is a contrast vector.
            # This contrast vector corresponds to the mean of the dependent
            # variable at the factor level.
            # For example, we would have one row that calculates the mean
            # for patients, and one for controls.

            lsmeans = pd.DataFrame(index=variable_levels, columns=dmat.columns)
            for level in variable_levels:
                reference_rows = reference_dmat.loc[grid[variable] == level]
                lsmeans.loc[level] = reference_rows.mean()

            value_dict = contrast["values"]
            names = [name for name in value_dict.keys() if name in variable_levels]
            values = [value_dict[name] for name in names]

            # If we wish to test the mean of each group against zero,
            # we can simply use these contrasts and be done.
            # To test a linear hypothesis such as patient-control=0,
            # which is expressed here as {"patient":1, "control":-1},
            # we translate it to a contrast vector by taking the linear
            # combination of the lsmeans contrasts.

            contrast_vector = lsmeans.loc[names].mul(values, axis=0).sum()
            contrast_matrix = pd.DataFrame([contrast_vector], columns=dmat.columns)

            contrast_name = f"{contrast['name']}"
            contrast_matrices.append((contrast_name, contrast_matrix))

    npts, nevs = dmat.shape

    if nevs >= npts:
        logger.warning(
            "Reverting to simple intercept only design. \n"
            f"nevs ({nevs}) >= npts ({npts})"
        )
        return intercept_only_design(len(subjects))

    regressor_list: dict[str, list[float]] = OrderedDict(
        (str(name), values)
        for name, values in dmat.to_dict(orient="list", into=OrderedDict).items()
    )
    contrast_list, contrast_numbers, contrast_names = _make_contrasts_list(
        contrast_matrices
    )

    return Design(regressor_list, contrast_list, contrast_numbers, contrast_names)


def make_design_tsv(
    regressor_list: dict[str, list[float]],
    contrast_list: list[tuple],
    row_index: list[str],
) -> tuple[Path, Path]:
    design_matrix, contrast_matrices = parse_design(regressor_list, contrast_list)
    design_matrix.index = pd.Index(row_index)

    design_tsv = Path.cwd() / "design.tsv"
    design_matrix.to_csv(design_tsv, sep="\t", index=True, na_rep="n/a", header=True)

    index: list[str] = list()
    for contrast_name, contrast_matrix in contrast_matrices.items():
        for _ in range(contrast_matrix.shape[0]):
            index.append(contrast_name)

    contrast_data_frame = pd.DataFrame(
        np.concatenate(list(contrast_matrices.values()), axis=0),
        index=index,
        columns=design_matrix.columns,
    )

    contrast_tsv = Path.cwd() / "contrasts.tsv"
    contrast_data_frame.to_csv(
        contrast_tsv,
        sep="\t",
        index=True,
        na_rep="n/a",
        header=True,
    )

    return design_tsv, contrast_tsv
