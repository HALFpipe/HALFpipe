# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from abc import ABC, abstractmethod
from typing import Dict, Generator, List, Optional, Tuple

import numpy as np
import nibabel as nib


class ModelAlgorithm(ABC):
    outputs: List[str] = list()

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
    def write_outputs(ref_img: nib.Nifti1Image, cmatdict: Dict, voxel_results: Dict) -> Dict:
        raise NotImplementedError()


def listwise_deletion(*args: np.ndarray) -> Generator[np.ndarray, None, None]:
    available = np.all(
        np.concatenate(
            [np.isfinite(a) for a in args],
            axis=1
        ),
        axis=1
    )

    for a in args:
        yield a[available, ...]


def demean(a: np.ndarray) -> np.ndarray:
    b = a.copy()

    assert np.allclose(b[:, 0], 1.0), "Intercept is missing"

    b[:, 1:] -= np.nanmean(b, axis=0)[np.newaxis, 1:]

    return b
