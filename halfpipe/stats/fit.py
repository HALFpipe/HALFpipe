# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from typing import List, Dict, Optional, Tuple

from pathlib import Path
from multiprocessing import get_context
from contextlib import nullcontext

import numpy as np
import nibabel as nib
from tqdm import tqdm

from ..io import parse_design
from ..utils import atleast_4d
from .algorithms import algorithms

ctx = get_context("forkserver")


def voxel_calc(voxel_data):
    algorithms_to_run, c, y, z, s, cmatdict = voxel_data

    return {
        a: algorithms[a].voxel_calc(c, y, z, s, cmatdict) for a in algorithms_to_run
    }


def fit(
    cope_files: List[Path],
    var_cope_files: Optional[List[Path]],
    mask_files: List[Path],
    regressors: Dict[str, List[float]],
    contrasts: List[Tuple],
    algorithms_to_run: List[str],
    num_threads: int,
) -> Dict:
    # load data
    cope_data = [
        atleast_4d(nib.load(f).get_fdata())
        for f in cope_files
    ]
    copes = np.concatenate(cope_data, axis=3)

    mask_data = [
        atleast_4d(np.asanyarray(nib.load(f).dataobj).astype(np.bool))
        for f in mask_files
    ]
    masks = np.concatenate(mask_data, axis=3)

    if var_cope_files is not None:
        var_cope_data = [
            atleast_4d(nib.load(f).get_fdata())
            for f in var_cope_files
        ]
        var_copes = np.concatenate(var_cope_data, axis=3)
    else:
        var_copes = np.zeros_like(copes)

    shape = copes[..., 0].shape

    dmat, cmatdict = parse_design(regressors, contrasts)

    nevs = dmat.columns.size

    # update the masks
    masks = np.logical_and(masks, np.isfinite(copes))
    masks = np.logical_and(masks, np.isfinite(var_copes))

    # prepare voxelwise generator
    def gen_voxel_data():
        def ensure_row_vector(x):
            return np.ravel(x)[:, np.newaxis]

        for coordinate in np.ndindex(*shape):
            available = ensure_row_vector(masks[coordinate])
            missing = np.logical_not(available)

            npts = np.count_nonzero(available)
            if npts < nevs + 1:  # need at least one degree of freedom
                continue

            y = ensure_row_vector(copes[coordinate])
            y[missing] = np.nan

            s = ensure_row_vector(var_copes[coordinate])
            s[missing] = np.nan

            z = dmat.to_numpy(dtype=np.float64)

            yield algorithms_to_run, coordinate, y, z, s, cmatdict

    voxel_data = gen_voxel_data()

    # setup run
    if num_threads < 2:
        cm = nullcontext()
        it = map(voxel_calc, voxel_data)
    else:
        cm = ctx.Pool(processes=num_threads)
        it = cm.imap_unordered(voxel_calc, voxel_data)

    # run
    voxel_results = dict()
    with cm:
        for x in tqdm(it, unit="voxels"):
            if x is None:
                continue

            for a, d in x.items():  # transpose
                if d is None:
                    continue

                if a not in voxel_results:
                    voxel_results[a] = dict()

                for k, v in d.items():
                    if v is None:
                        continue

                    if k not in voxel_results[a]:
                        voxel_results[a][k] = dict()

                    voxel_results[a][k].update(v)

    ref_image = nib.squeeze_image(nib.load(cope_files[0]))

    output_files = dict()
    for a, v in voxel_results.items():
        output_files.update(
            algorithms[a].write_outputs(ref_image, cmatdict, v)
        )

    return output_files
