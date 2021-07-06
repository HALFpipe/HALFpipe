# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from typing import List, Dict, Optional, Tuple

from collections import defaultdict
import os
from pathlib import Path
from multiprocessing import get_context
from multiprocessing.pool import Pool
from contextlib import nullcontext

import numpy as np
import nibabel as nib
from tqdm import tqdm

from ..io import parse_design
from ..utils import atleast_4d
from .algorithms import algorithms, make_algorithms_set
from ..logging import Context

ctx = get_context("forkserver")


def initializer(loggingargs, host_env):
    from ..logging import setup as setuplogging
    setuplogging(**loggingargs)

    os.environ.update(host_env)


def voxel_calc(voxel_data):
    algorithm_set, c, y, z, s, cmatdict = voxel_data

    return {
        a: algorithms[a].voxel_calc(c, y, z, s, cmatdict) for a in algorithm_set
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
        atleast_4d(np.asanyarray(nib.load(f).dataobj).astype(bool))
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

    algorithm_set = make_algorithms_set(algorithms_to_run)

    if dmat.shape[1] == 1:  # do not run if we do not have regressors
        algorithm_set -= frozenset(["mcartest"])

    # prepare voxelwise generator
    def gen_voxel_data():
        def ensure_row_vector(x):
            return np.ravel(x)[:, np.newaxis]

        for coordinate in np.ndindex(*shape):
            available = ensure_row_vector(masks[coordinate])
            missing = np.logical_not(available)

            npts = np.count_nonzero(available)
            if npts < nevs + 3:  # need at least three degrees of freedom
                continue

            y = ensure_row_vector(copes[coordinate])
            y[missing] = np.nan

            s = ensure_row_vector(var_copes[coordinate])
            s[missing] = np.nan

            z = dmat.to_numpy(dtype=np.float64)

            yield algorithm_set, coordinate, y, z, s, cmatdict

    voxel_data = gen_voxel_data()

    # setup run
    if num_threads < 2:
        cm = nullcontext()
        it = map(voxel_calc, voxel_data)
    else:
        cm = ctx.Pool(
            processes=num_threads,
            initializer=initializer,
            initargs=(
                Context.loggingargs(),
                dict(os.environ),
            ),
        )
        it = cm.imap_unordered(voxel_calc, voxel_data)

    # run
    voxel_results = defaultdict(lambda: defaultdict(dict))
    with cm:
        for x in tqdm(it, unit="voxels"):
            if x is None:
                continue

            for a, d in x.items():  # transpose
                if d is None:
                    continue

                for k, v in d.items():
                    if v is None:
                        continue

                    voxel_results[a][k].update(v)

        if isinstance(cm, Pool):
            cm.close()
            cm.join()

    ref_image = nib.squeeze_image(nib.load(cope_files[0]))

    output_files = dict()
    for a, v in voxel_results.items():
        output_files.update(
            algorithms[a].write_outputs(ref_image, cmatdict, v)
        )

    return output_files
