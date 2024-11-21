# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import abstractmethod
from collections import Counter
from dataclasses import dataclass, fields
from enum import Enum, auto
from functools import cached_property, partial
from pathlib import Path
from typing import Any, Self, Sequence

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
from ....utils.multiprocessing import IterationOrder, Pool, make_pool_or_null_context


def load_atlas(
    image_path: Path | str,
    labels_path: Path | str,
) -> tuple[dict[int, str], nib.analyze.AnalyzeImage]:
    image_path = Path(image_path)

    labels_frame = read_spreadsheet(labels_path)
    labels: dict[int, str] = dict()
    for label_tuple in labels_frame.itertuples(index=False):
        # First column is the index, second is the name.
        labels[int(label_tuple[0])] = format_like_bids(str(label_tuple[1]))

    image = nib.nifti1.load(image_path)
    return labels, image


class Statistic(Enum):
    z = auto()
    effect = auto()
    standardized_effect = auto()
    cohens_d = auto()


@dataclass
class ImagePaths:
    effect: Path
    mask: Path

    variance: Path | None = None
    sigmasquareds: Path | None = None
    t: Path | None = None
    dof: Path | None = None
    z: Path | None = None

    @cached_property
    def effect_image(self) -> nib.analyze.AnalyzeImage:
        return nib.nifti1.load(self.effect)

    @cached_property
    def mask_image(self) -> nib.analyze.AnalyzeImage:
        return nib.nifti1.load(self.mask)

    @property
    def mask_data(self) -> npt.NDArray[np.bool_]:
        return np.asanyarray(self.mask_image.dataobj, dtype=bool)

    def get_data_image(self, statistic: Statistic) -> tuple[Statistic, nib.analyze.AnalyzeImage]:
        if statistic == Statistic.effect:
            return statistic, self.effect_image
        elif statistic == Statistic.cohens_d:
            if self.sigmasquareds is None:
                logger.info(f'Cannot find sigmasquareds image for image "{self.effect}"')
                return self.get_data_image(Statistic.effect)
            effect_image = self.effect_image
            sigmasquareds_image = nib.nifti1.load(self.sigmasquareds)

            effect = effect_image.get_fdata()
            sigmasquareds = sigmasquareds_image.get_fdata()
            mask = self.mask_data

            d = np.zeros_like(effect)
            d[mask] = effect[mask] / np.sqrt(sigmasquareds[mask])

            d_image: Any = new_img_like(effect_image, d, copy_header=True)
            return Statistic.cohens_d, d_image
        elif statistic == Statistic.z:
            if self.z is None:
                logger.info(f'Cannot find z-statistic image for image "{self.effect}"')
                return self.get_data_image(Statistic.effect)
            return Statistic.z, nib.nifti1.load(self.z)
        elif statistic == Statistic.standardized_effect:
            if self.variance is None:
                logger.info(f'Cannot find variance image for image "{self.effect}"')
                return self.get_data_image(Statistic.z)
            if self.dof is None:
                logger.info(f'Cannot find degrees of freedom image for image "{self.effect}"')
                return self.get_data_image(Statistic.z)

            effect_image = self.effect_image
            variance_image = nib.nifti1.load(self.variance)
            dof_image = nib.nifti1.load(self.dof)

            effect = effect_image.get_fdata()
            variance = variance_image.get_fdata()
            dof = dof_image.get_fdata()
            mask = self.mask_data

            t = np.zeros_like(effect)
            t[mask] = effect[mask] / np.sqrt(variance[mask])
            standardized_coefficient_fisherz = np.zeros_like(effect)
            standardized_coefficient_fisherz[mask] = np.arctanh(t[mask] / np.sqrt(np.square(t[mask]) + dof[mask]))

            standardized_coefficient_image: Any = new_img_like(
                effect_image, standardized_coefficient_fisherz, copy_header=True
            )
            return Statistic.standardized_effect, standardized_coefficient_image
        else:
            raise NotImplementedError


@dataclass
class AtlasSignals:
    array: npt.NDArray[np.float64]
    coverages: npt.NDArray[np.float64]
    statistic: str | None = None


@dataclass
class Atlas:
    name: str
    image: nib.analyze.AnalyzeImage
    labels: dict[int, str]

    @abstractmethod
    def apply(self, image_paths: ImagePaths) -> AtlasSignals:
        raise NotImplementedError


@dataclass
class DiscreteAtlas(Atlas):
    statistic: Statistic

    def apply(self, image_paths: ImagePaths) -> AtlasSignals:
        statistic, data_image = image_paths.get_data_image(self.statistic)
        signals, coverage = mean_signals(
            data_image,
            self.image,
            mask_image=image_paths.mask_image,
            output_coverage=True,
        )

        if statistic == Statistic.standardized_effect:
            # Undo Fisher z-transformation
            signals = np.tanh(signals)

        return AtlasSignals(signals, np.array(coverage), statistic.name)

    @classmethod
    def from_args(
        cls,
        name: str,
        statistic: str,
        image_path: str,
        labels_path: str,
    ) -> Self:
        labels, image = load_atlas(image_path, labels_path)
        return cls(name, image, labels, Statistic[statistic])


@dataclass
class ProbabilisticAtlas(Atlas):
    def apply(self, image_paths: ImagePaths) -> AtlasSignals:
        var_cope_files = None
        if image_paths.variance is not None:
            var_cope_files = [image_paths.variance]
        cope_img, var_cope_img = load_data([image_paths.effect], var_cope_files, [image_paths.mask], quiet=True)
        signals, coverage = mode_signals(cope_img, var_cope_img, self.image, output_coverage=True)
        return AtlasSignals(signals, coverage)

    @classmethod
    def from_args(
        cls,
        name: str,
        image_path: str,
        labels_path: str,
    ) -> Self:
        labels, image = load_atlas(image_path, labels_path)
        return cls(name, image, labels)


def export(
    column_prefix: str | None,
    subjects: list[str],
    images: dict[str, list[Path]],
    regressors: dict[str, list[float]],
    contrasts: Sequence[TContrast | FContrast],
    atlases: list[Atlas],
    num_threads: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    covariate_frame, _ = parse_design(regressors, contrasts)
    covariate_frame.index = pd.Index(subjects)

    signals: dict[str, npt.NDArray] = dict()
    coverages: dict[str, npt.NDArray] = dict()

    # Prepare for parallel processing
    cope_paths = images["effect"]
    num_inputs = len(cope_paths)
    inner = partial(get_signals, atlases)

    valid_fields = {field.name for field in fields(ImagePaths)}
    for key in list(images.keys()):
        if key not in valid_fields:
            logger.warning(f"Ignoring '{key}' in images for export")
            del images[key]
    image_paths_list = [
        ImagePaths(**dict(zip(images.keys(), paths, strict=True))) for paths in zip(*images.values(), strict=True)
    ]

    cm, iterator = make_pool_or_null_context(
        image_paths_list,
        callable=inner,
        num_threads=num_threads,
        iteration_order=IterationOrder.ORDERED,
    )
    with cm:
        # Top list level is subjects, second level is atlases
        signal_rows: list[list[AtlasSignals]] = list(
            tqdm(iterator, unit="images", desc="extracting signals", total=num_inputs)
        )

    if isinstance(cm, Pool):
        cm.terminate()
        cm.join()

    # Transpose subjects and atlases
    signal_columns = list(list(c) for c in zip(*signal_rows, strict=False))

    for atlas, signal_column in zip(atlases, signal_columns, strict=False):
        # Unpack signal/coverage
        statistics_counter: Counter[str | None] = Counter(signal.statistic for signal in signal_column)
        most_common_statistic, _ = statistics_counter.most_common(1)[0]
        if len(statistics_counter) > 1:
            signal_column = [signal for signal in signal_column if signal.statistic == most_common_statistic]
            logger.warning(
                "Inconsistent statistics were used across subjects. "
                "Please check that processing completed for all subjects "
                f"and that all required outputs are available. Using {most_common_statistic} "
                f"as it is the most common ({statistics_counter})"
            )
        statistic = most_common_statistic
        signal_array: npt.NDArray = np.vstack([signal.array for signal in signal_column])
        coverage_array: npt.NDArray = np.vstack([signal.coverages for signal in signal_column])

        for i in range(signal_array.shape[1]):
            label = atlas.labels[i + 1]
            column = f"{column_prefix}_{atlas.name}_label-{label}"
            if statistic is not None:
                column = f"{column}_stat-{format_like_bids(statistic)}"
            signals[column] = signal_array[:, i]
            coverages[column] = coverage_array[:, i]

    signals_frame = pd.DataFrame.from_dict(signals)
    signals_frame.index = pd.Index(subjects)
    atlas_coverage_frame = pd.DataFrame.from_dict(coverages)
    atlas_coverage_frame.index = pd.Index(subjects)

    logger.info(f"Exported {signals_frame.shape[1]} signals and {covariate_frame.shape[1]} covariates")

    return signals_frame, covariate_frame, atlas_coverage_frame


def get_signals(
    atlases: list[Atlas],
    image_paths: ImagePaths,
) -> list[AtlasSignals]:
    return [atlas.apply(image_paths) for atlas in atlases]
