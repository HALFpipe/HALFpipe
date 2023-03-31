# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.image import new_img_like


class ModelAlgorithm(ABC):
    model_outputs: List[str] = list()
    contrast_outputs: List[str] = list()

    @staticmethod
    @abstractmethod
    def voxel_calc(
        coordinate: Tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: Dict,
    ) -> Optional[Dict]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def write_outputs(
        ref_img: nib.Nifti1Image, cmatdict: Dict, voxel_results: Dict
    ) -> Dict:
        raise NotImplementedError()

    @classmethod
    def write_map(cls, ref_img: nib.Nifti1Image, out_name: str, series: pd.Series):
        coordinates = series.index.tolist()
        values = series.values

        shape: List[int] = list(ref_img.shape[:3])

        (k,) = set(
            (1,)
            if isinstance(value, (int, float))
            else (len(value),)
            if isinstance(value, (list, tuple))
            else value.shape
            for value in values
        )
        shape.extend(k)

        if len(shape) == 4 and shape[-1] == 1:
            shape = shape[:3]  # squeeze

        if out_name.startswith("mask"):
            arr = np.full(shape, False)

        else:
            arr = np.full(shape, np.nan, dtype=np.float64)

        for coordinate, value in zip(coordinates, values):
            arr[coordinate] = value

        img = new_img_like(ref_img, arr, copy_header=True)
        assert isinstance(img.header, nib.Nifti1Header)
        img.header.set_data_dtype(np.float64)

        fname = Path.cwd() / f"{out_name}.nii.gz"
        nib.save(img, fname)

        return fname


def listwise_deletion(*args: np.ndarray) -> Generator[np.ndarray, None, None]:
    available = np.all(np.concatenate([np.isfinite(a) for a in args], axis=1), axis=1)

    for a in args:
        yield a[available, ...]


def demean(a: np.ndarray) -> np.ndarray:
    b = a.copy()

    assert np.allclose(b[:, 0], 1.0), "Intercept is missing"

    b[:, 1:] -= np.nanmean(b, axis=0)[np.newaxis, 1:]

    return b
