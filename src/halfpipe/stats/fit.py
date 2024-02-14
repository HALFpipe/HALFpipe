# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from pathlib import Path
from typing import Iterator, Literal, NamedTuple, Sequence, Type

import nibabel as nib
import numpy as np
from nilearn.image import new_img_like
from numpy import typing as npt
from threadpoolctl import threadpool_limits
from tqdm.auto import tqdm

from ..design import FContrast, TContrast, parse_design
from ..utils.multiprocessing import make_pool_or_null_context
from .algorithms import algorithms, make_algorithms_dict
from .base import ModelAlgorithm


class VoxelData(NamedTuple):
    algorithm_dict: dict[str, Type[ModelAlgorithm]]
    coordinate: tuple[int, int, int]
    effect: npt.NDArray[np.float64]
    design_matrix: npt.NDArray[np.float64]
    variance: npt.NDArray[np.float64]
    contrast_matrices: dict[str, npt.NDArray[np.float64]]


def voxel_calc(voxel_data: VoxelData) -> dict:
    with threadpool_limits(limits=1, user_api="blas"):
        return {
            name: algorithm.voxel_calc(
                voxel_data.coordinate,
                voxel_data.effect,
                voxel_data.design_matrix,
                voxel_data.variance,
                voxel_data.contrast_matrices,
            )
            for name, algorithm in voxel_data.algorithm_dict.items()
        }


def load_data(
    cope_files: list[Path],
    var_cope_files: list[Path] | None,
    mask_files: list[Path],
    quiet: bool | None = None,
) -> tuple[nib.analyze.AnalyzeImage, nib.analyze.AnalyzeImage]:
    if len(cope_files) != len(mask_files):
        raise ValueError(f"Number of cope files ({len(cope_files)}) does not match number of mask files ({len(mask_files)})")

    # Load cope images.
    cope_imgs = [nib.funcs.squeeze_image(nib.nifti1.load(cope_file)) for cope_file in cope_files]

    (volume_shape,) = set(img.shape[:3] for img in cope_imgs)
    shape = volume_shape + (len(mask_files),)

    cope_data = np.empty(shape, dtype=float)
    for i, cope_img in enumerate(tqdm(cope_imgs, desc="loading cope images", leave=False, disable=quiet)):
        cope_data[..., i] = cope_img.get_fdata()

    # Load mask images.
    mask_data = np.empty(shape, dtype=bool)
    for i, mask_file in enumerate(tqdm(mask_files, desc="loading mask images", leave=False, disable=quiet)):
        mask_img = nib.funcs.squeeze_image(nib.nifti1.load(mask_file))
        mask_data[..., i] = np.asanyarray(mask_img.dataobj).astype(bool)

    # Load varcope images.
    var_cope_data = np.full(shape, np.nan, dtype=float)
    if var_cope_files is not None:
        if len(var_cope_files) != len(cope_files):
            raise ValueError(
                f"Number of var_cope files ({len(var_cope_files)}) does not match number of cope files ({len(cope_files)})"
            )
        for i, var_cope_file in enumerate(
            tqdm(
                var_cope_files,
                desc="loading var_cope images",
                leave=False,
                disable=quiet,
            )
        ):
            if var_cope_file is None:
                raise ValueError(f'Missing var_cope file corresponding to "{cope_files[i]}"')
            var_cope_img = nib.funcs.squeeze_image(nib.nifti1.load(var_cope_file))
            var_cope_data[..., i] = var_cope_img.get_fdata()

    # Update the masks.
    mask_data &= np.isfinite(cope_data)
    if var_cope_files is not None:
        mask_data &= np.isfinite(var_cope_data)

    # Zero out voxels that are not in the mask.
    cope_data[~mask_data] = np.nan
    var_cope_data[~mask_data] = np.nan

    # Create image objects.
    copes_img = new_img_like(cope_imgs[0], cope_data)
    var_copes_img = new_img_like(cope_imgs[0], var_cope_data)

    return copes_img, var_copes_img


def ensure_row_vector(x):
    return np.ravel(x)[:, np.newaxis]


def make_voxelwise_generator(
    copes_img: nib.analyze.AnalyzeImage,
    var_copes_img: nib.analyze.AnalyzeImage,
    regressors: dict[str, list[float]],
    contrasts: Sequence[TContrast | FContrast],
    algorithms_to_run: list[str],
) -> tuple[Iterator[VoxelData], dict]:
    shape = copes_img.shape[:3]

    copes = copes_img.get_fdata()
    var_copes = var_copes_img.get_fdata()

    dmat, contrast_matrices = parse_design(regressors, contrasts)
    regressor_count = dmat.columns.size

    algorithm_dict = make_algorithms_dict(algorithms_to_run)

    # Do not run the MCAR test if we do not have regressors.
    if dmat.shape[1] == 1:
        if "mcartest" in algorithm_dict:
            del algorithm_dict["mcartest"]

    # prepare voxelwise generator
    def gen_voxel_data():
        for x, y, z in np.ndindex(*shape):
            effect = ensure_row_vector(copes[x, y, z])

            sample_count = np.count_nonzero(np.isfinite(effect))
            # Skip if we don't have at least three degrees of freedom
            if sample_count < regressor_count + 3:
                continue

            variance = ensure_row_vector(var_copes[x, y, z])
            design_matrix = dmat.to_numpy(dtype=float)

            yield VoxelData(
                algorithm_dict=algorithm_dict,
                coordinate=(x, y, z),
                effect=effect,
                design_matrix=design_matrix,
                variance=variance,
                contrast_matrices=contrast_matrices,
            )

    return gen_voxel_data(), contrast_matrices


def fit(
    cope_files: list[Path],
    var_cope_files: list[Path] | None,
    mask_files: list[Path],
    regressors: dict[str, list[float]],
    contrasts: Sequence[TContrast | FContrast],
    algorithms_to_run: list[str],
    num_threads: int,
) -> dict[str, Sequence[Literal[False] | str]]:
    copes_img, var_copes_img = load_data(
        cope_files,
        var_cope_files,
        mask_files,
    )

    voxel_data, cmatdict = make_voxelwise_generator(
        copes_img,
        var_copes_img,
        regressors,
        contrasts,
        algorithms_to_run,
    )

    cm, iterator = make_pool_or_null_context(voxel_data, voxel_calc, num_threads=num_threads, chunksize=2**9)
    voxel_results: dict[str, dict] = defaultdict(lambda: defaultdict(dict))
    with cm:
        for x in tqdm(iterator, unit="voxels", desc="model fit"):
            if x is None:
                continue
            for algorithm, result in x.items():  # transpose
                if result is None:
                    continue
                for k, v in result.items():
                    if v is None:
                        continue
                    voxel_results[algorithm][k].update(v)

    ref_image = nib.funcs.squeeze_image(nib.nifti1.load(cope_files[0]))

    output_files: dict[str, Sequence[Literal[False] | str]] = dict()
    for a, v in voxel_results.items():
        output_files.update(algorithms[a].write_outputs(ref_image, cmatdict, v))

    return output_files
