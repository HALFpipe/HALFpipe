# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict
from contextlib import nullcontext
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import ContextManager, Iterable, Literal, Self, Sequence

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.image import new_img_like
from numpy import typing as npt
from tqdm.auto import tqdm

from ....design import FContrast, TContrast, parse_design
from ....ingest.spreadsheet import read_spreadsheet
from ....logging import logger
from ....signals import mean_signals, mode_signals
from ....stats.fit import load_data
from ....utils.format import format_like_bids
from ....utils.multiprocessing import Pool


@dataclass
class Atlas:
    type: Literal["atlas", "modes"]
    name: str
    image: nib.analyze.AnalyzeImage
    labels: dict[int, str]

    @classmethod
    def from_args(
        cls,
        type: Literal["atlas", "modes"],
        name: str,
        image_path: Path | str,
        labels_path: Path | str,
    ) -> Self:
        image_path = Path(image_path)

        labels_frame = read_spreadsheet(labels_path)
        labels: dict[int, str] = dict()
        for label_tuple in labels_frame.itertuples(index=False):
            # First columnn is the index, second is the name.
            labels[int(label_tuple[0])] = format_like_bids(str(label_tuple[1]))

        image = nib.nifti1.load(image_path)
        if not isinstance(image, nib.analyze.AnalyzeImage):
            raise ValueError(f'"{image_path}" is not a nifti image')
        return cls(type, name, image, labels)


def export(
    column_prefix: str | None,
    subjects: list[str],
    cope_files: list[Path],
    var_cope_files: Sequence[Path | None] | None,
    mask_files: list[Path],
    regressors: dict[str, list[float]],
    contrasts: Sequence[TContrast | FContrast],
    atlases: list[Atlas],
    num_threads: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    covariate_frame, _ = parse_design(regressors, contrasts)
    covariate_frame.index = pd.Index(subjects)

    signals: dict[str, npt.NDArray] = OrderedDict()
    coverages: dict[str, npt.NDArray] = OrderedDict()

    # Prepare for parallel processing.
    num_inputs = len(cope_files)
    if var_cope_files is None:
        var_cope_files = [None] * num_inputs
    inner = partial(get_signals, atlases)
    arg_tuples = zip(cope_files, var_cope_files, mask_files)

    # Only start a pool if we are using more than one thread.
    if num_threads < 2:
        pool: Pool | None = None
        it: Iterable = map(inner, arg_tuples)
        cm: ContextManager = nullcontext()
    else:
        pool = Pool(processes=num_threads)
        it = pool.imap(inner, arg_tuples)
        cm = pool

    with cm:
        # Top list level is subjects, second level is atlases.
        signal_rows: list[list[tuple[npt.NDArray, npt.NDArray]]] = list(
            tqdm(it, unit="images", desc="extracting signals", total=num_inputs)
        )

    if pool is not None:
        pool.terminate()
        pool.join()

    # Transpose subjects and atlases.
    signal_columns = (list(c) for c in zip(*signal_rows))
    for atlas, signal_column in zip(atlases, signal_columns):
        # Unpack signal/coverage.
        signal_list, coverage_list = (list(c) for c in zip(*signal_column))
        signal_array: npt.NDArray = np.vstack(signal_list)
        coverage_array: npt.NDArray = np.vstack(coverage_list)

        for i in range(signal_array.shape[1]):
            label = atlas.labels[i + 1]
            signals[f"{column_prefix}_{atlas.name}_label-{label}"] = signal_array[:, i]
            coverages[f"{column_prefix}_{atlas.name}_label-{label}"] = coverage_array[
                :, i
            ]

    signals_frame = pd.DataFrame.from_dict(signals)
    signals_frame.index = pd.Index(subjects)
    atlas_coverage_frame = pd.DataFrame.from_dict(coverages)
    atlas_coverage_frame.index = pd.Index(subjects)

    logger.info(
        f"Exported {signals_frame.shape[1]} signals and {covariate_frame.shape[1]} covariates"
    )

    return signals_frame, covariate_frame, atlas_coverage_frame


def get_signals(
    atlases: list[Atlas],
    path_tuple: tuple[Path, Path | None, Path],
) -> list[tuple[npt.NDArray, npt.NDArray]]:
    (cope_file, var_cope_file, mask_file) = path_tuple

    var_cope_files = None
    if var_cope_file is not None:
        var_cope_files = [var_cope_file]
    cope_img, var_cope_img = load_data(
        [cope_file], var_cope_files, [mask_file], quiet=True
    )

    results: list[tuple[npt.NDArray, npt.NDArray]] = list()
    for atlas in atlases:
        if atlas.type == "atlas":
            cope_data = np.asanyarray(cope_img.dataobj)
            mask_img = new_img_like(cope_img, np.isfinite(cope_data))
            s, c = mean_signals(
                cope_img,
                atlas.image,
                mask_image=mask_img,
                output_coverage=True,
            )
            results.append((s, np.array(c)))
        elif atlas.type == "modes":
            results.append(
                mode_signals(cope_img, var_cope_img, atlas.image, output_coverage=True)
            )
        else:
            raise ValueError(f'Unknown atlas type "{atlas.type}".')

    return results
