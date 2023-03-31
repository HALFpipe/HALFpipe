# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict
from pathlib import Path
from typing import Any

import nibabel as nib
import pandas as pd
from numpy import typing as npt
from threadpoolctl import threadpool_limits

from ....ingest.design import parse_design
from ....ingest.spreadsheet import read_spreadsheet
from ....signals import mean_signals, mode_signals
from ....stats.fit import load_data


def export(
    row_index: list[str],
    cope_files: list[Path],
    var_cope_files: list[Path] | None,
    mask_files: list[Path],
    regressors: dict[str, list[float]],
    contrasts: list[tuple],
    exports: list[tuple[str, str, str, str]],
    num_threads: int,
) -> dict[str, Any]:
    copes_img, var_copes_img = load_data(cope_files, var_cope_files, mask_files)
    covariate_frame, _ = parse_design(regressors, contrasts)
    covariate_frame.index = pd.Index(row_index)

    variables: dict[str, npt.NDArray] = OrderedDict()
    metadata: dict[str, Any] = dict(coverage=dict())

    for export_name, export_type, image_str, labels_path in exports:
        image_path = Path(image_str)

        labels_frame = read_spreadsheet(labels_path)

        labels: dict[int, str] = dict()
        for label_tuple in labels_frame.itertuples(index=False):
            # First columnn is the index, second is the name.
            labels[int(label_tuple[0])] = str(label_tuple[1])

        signals: npt.NDArray | None = None

        image = nib.load(image_path)
        with threadpool_limits(limits=num_threads, user_api="blas"):
            if export_type == "atlas":
                signals, coverage = mean_signals(
                    image,
                    copes_img,
                    output_coverage=True,
                )
                metadata["coverage"][export_name] = {
                    labels[i + 1]: c for i, c in enumerate(coverage)
                }
            elif export_type == "modes":
                signals = mode_signals(copes_img, var_copes_img, image)

        if signals is None:
            raise ValueError(f'Could not export "{export_type}" for "{image_str}".')

        signal_count = signals.shape[1]
        for i in range(signal_count):
            variables[f"{export_name}[{labels[i + 1]}]"] = signals[:, i]

    variable_frame = pd.DataFrame.from_dict(variables)
    variable_frame.index = pd.Index(row_index)

    variable_path = Path.cwd() / "variables.tsv"
    variable_frame.to_csv(variable_path, sep="\t", index=True)

    covariate_path = Path.cwd() / "covariates.tsv"
    covariate_frame.to_csv(covariate_path, sep="\t", index=True)

    return dict(
        variables=str(variable_path),
        covariates=str(covariate_path),
        metadata=metadata,
    )
