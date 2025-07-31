# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Literal

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.image import new_img_like


class ModelAlgorithm(ABC):
    model_outputs: list[str] = list()
    contrast_outputs: list[str] = list()

    @staticmethod
    @abstractmethod
    def voxel_calc(
        coordinate: tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: dict,
    ) -> dict | None:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def write_outputs(
        cls, reference_image: nib.analyze.AnalyzeImage, contrast_matrices: dict, voxel_results: dict
    ) -> dict[str, list[Literal[False] | str]]:
        raise NotImplementedError()

    @classmethod
    def write_map(cls, reference_image: nib.analyze.AnalyzeImage, out_name: str, series: pd.Series) -> Path:
        coordinates = series.index.tolist()
        values = series.values.tolist()

        shape: list[int] = list(reference_image.shape[:3])
        (k,) = set(
            ((1,) if isinstance(value, (int, float)) else (len(value),) if isinstance(value, (list, tuple)) else value.shape)
            for value in values
        )
        shape.extend(k)

        if len(shape) == 4 and shape[-1] == 1:
            shape = shape[:3]  # squeeze

        if out_name.startswith("mask"):
            array = np.full(shape, False, dtype=np.bool_)
        else:
            array = np.full(shape, np.nan, dtype=np.float64)

        array[*zip(*coordinates, strict=False)] = np.stack(values).squeeze()

        image = new_img_like(reference_image, array, copy_header=True)
        if not isinstance(image.header, nib.nifti1.Nifti1Header):
            raise TypeError("Only nifti1 headers are supported")
        image.header.set_data_dtype(np.float64)

        image_path = Path.cwd() / f"{out_name}.nii.gz"
        nib.loadsave.save(image, image_path)

        return image_path


def listwise_deletion(*args: np.ndarray) -> Iterator[np.ndarray]:
    available = np.all(np.concatenate([np.isfinite(a) for a in args], axis=1), axis=1)

    for a in args:
        yield a[available, ...]


def demean(a: np.ndarray) -> np.ndarray:
    b = a.copy()

    assert np.allclose(b[:, 0], 1.0), "Intercept is missing"

    b[:, 1:] -= np.nanmean(b, axis=0)[np.newaxis, 1:]

    return b
