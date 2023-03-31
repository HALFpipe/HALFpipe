# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
from typing import ContextManager, Iterator

import nibabel as nib
import numpy as np
from nilearn.image import new_img_like
from threadpoolctl import threadpool_limits
from tqdm.auto import tqdm

from ..ingest.design import parse_design
from ..utils.multiprocessing import Pool
from .algorithms import algorithms, make_algorithms_set


def voxel_calc(voxel_data):
    with threadpool_limits(limits=1, user_api="blas"):
        algorithm_set, c, y, z, s, cmatdict = voxel_data
        return {
            a: algorithms[a].voxel_calc(c, y, z, s, cmatdict) for a in algorithm_set
        }


def load_data(
    cope_files: list[Path],
    var_cope_files: list[Path] | None,
    mask_files: list[Path],
) -> tuple[nib.Nifti1Image, nib.Nifti1Image]:
    if len(cope_files) != len(mask_files):
        raise ValueError(
            f"Number of cope files ({len(cope_files)}) does not match number of mask files ({len(mask_files)})"
        )

    # Load cope images.
    cope_imgs = [nib.load(cope_file) for cope_file in cope_files]

    (volume_shape,) = set(img.shape[:3] for img in cope_imgs)
    shape = volume_shape + (len(mask_files),)

    cope_data = np.empty(shape, dtype=float)
    for i, cope_img in enumerate(
        tqdm(cope_imgs, desc="loading cope images", leave=False)
    ):
        cope_data[..., i] = cope_img.get_fdata()

    # Load mask images.
    mask_data = np.empty(shape, dtype=bool)
    for i, mask_file in enumerate(
        tqdm(mask_files, desc="loading mask images", leave=False)
    ):
        mask_img = nib.load(mask_file)
        mask_data[..., i] = np.asanyarray(mask_img.dataobj).astype(bool)

    # Load varcope images.
    var_cope_data = np.full(shape, np.nan, dtype=float)
    if var_cope_files is not None:
        if len(var_cope_files) != len(cope_files):
            raise ValueError(
                f"Number of variance cope files ({len(var_cope_files)}) does not match number of cope files ({len(cope_files)})"
            )
        for i, var_cope_file in enumerate(
            tqdm(var_cope_files, desc="loading varcope images", leave=False)
        ):
            var_cope_img = nib.load(var_cope_file)
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


def make_voxelwise_generator(
    copes_img: nib.Nifti1Image,
    var_copes_img: nib.Nifti1Image,
    regressors: dict[str, list[float]],
    contrasts: list[tuple],
    algorithms_to_run: list[str],
) -> tuple[Iterator, dict]:
    shape = copes_img.shape[:3]

    copes = copes_img.get_fdata()
    var_copes = var_copes_img.get_fdata()

    dmat, cmatdict = parse_design(regressors, contrasts)
    nevs = dmat.columns.size

    algorithm_set = make_algorithms_set(algorithms_to_run)

    # Do not run the MCAR test if we do not have regressors.
    if dmat.shape[1] == 1:
        algorithm_set -= frozenset(["mcartest"])

    # prepare voxelwise generator
    def gen_voxel_data():
        def ensure_row_vector(x):
            return np.ravel(x)[:, np.newaxis]

        for coordinate in np.ndindex(*shape):
            y = ensure_row_vector(copes[coordinate])

            npts = np.count_nonzero(np.isfinite(y))
            if npts < nevs + 3:  # need at least three degrees of freedom
                continue

            s = ensure_row_vector(var_copes[coordinate])
            z = dmat.to_numpy(dtype=float)

            yield algorithm_set, coordinate, y, z, s, cmatdict

    return gen_voxel_data(), cmatdict


def fit(
    row_index: list[str],
    cope_files: list[Path],
    var_cope_files: list[Path] | None,
    mask_files: list[Path],
    regressors: dict[str, list[float]],
    contrasts: list[tuple],
    algorithms_to_run: list[str],
    num_threads: int,
) -> dict[str, str]:
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

    # setup run
    if num_threads < 2:
        pool: Pool | None = None
        iterator: Iterator = map(voxel_calc, voxel_data)
        cm: ContextManager = nullcontext()
    else:
        pool = Pool(processes=num_threads)
        iterator = pool.imap_unordered(voxel_calc, voxel_data)
        cm = pool

    # run
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

    ref_image = nib.squeeze_image(nib.load(cope_files[0]))

    output_files = dict()
    for a, v in voxel_results.items():
        output_files.update(algorithms[a].write_outputs(ref_image, cmatdict, v))

    return output_files
