# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path

import nibabel as nib
import numpy as np
import scipy.spatial
import scipy.stats
from numpy import typing as npt

from halfpipe.utils.nipype import run_workflow
from halfpipe.workflows.features.falff import compute_falff, init_falff_wf


def test_compute_falff(tmp_path: Path):
    os.chdir(tmp_path)

    mask = np.array([True, True, True, True, False], dtype=np.bool_)
    filtered = np.array([1, 2, np.nan, 4, 0], dtype=np.float64)
    unfiltered = np.array([0.5, np.inf, 0.125, 0, 0], dtype=np.float64)

    mask_file = "mask.nii.gz"
    nib.nifti1.Nifti1Image(mask.astype(np.uint8), affine=np.eye(4)).to_filename(str(mask_file))

    filtered_file = "filtered.nii.gz"
    nib.nifti1.Nifti1Image(filtered, affine=np.eye(4)).to_filename(str(filtered_file))

    unfiltered_file = "unfiltered.nii.gz"
    nib.nifti1.Nifti1Image(unfiltered, affine=np.eye(4)).to_filename(str(unfiltered_file))

    mask_file, falff_file = compute_falff(mask_file, filtered_file, unfiltered_file)
    mask = np.asanyarray(nib.nifti1.load(mask_file).dataobj, dtype=np.bool_)
    falff = nib.nifti1.load(falff_file).get_fdata()

    np.testing.assert_allclose(falff, np.array([2, 0, 0, 0, 0], dtype=np.float64))
    np.testing.assert_equal(mask, np.array([True, False, False, False, False], dtype=np.bool_))


def make_spherical_mask(k: int) -> npt.NDArray[np.bool_]:
    c = np.arange(k)
    meshgrid = tuple(map(np.ravel, np.meshgrid(c, c, c)))
    coordinates = np.stack(meshgrid, axis=-1)

    m = coordinates.mean()
    center = np.array([[m, m, m]])

    mask = np.zeros((k, k, k), dtype=np.bool_)
    distance = scipy.spatial.distance.cdist(coordinates, center, metric="euclidean").ravel()
    mask[meshgrid] = distance < 3
    return mask


def test_falff_wf(tmp_path: Path):
    """Generate a spherical mask and synthetic time series data to test init_falff_wf"""
    os.chdir(tmp_path)
    rng = np.random.default_rng(0)

    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)

    wf = init_falff_wf(workdir=workdir, fwhm=0.0)
    wf.base_dir = workdir
    inputnode = wf.get_node("inputnode")
    assert inputnode is not None
    unfiltered_inputnode = wf.get_node("unfiltered_inputnode")
    assert unfiltered_inputnode is not None

    k = 10
    mask = make_spherical_mask(k)
    n = mask.sum()

    target = np.zeros((k, k, k), dtype=np.float64)
    target[mask] = scipy.stats.zscore(rng.gamma(2, 2, size=n))

    time_series = rng.normal(size=(k, k, k, 1000))
    time_series /= np.std(time_series, axis=-1)[..., np.newaxis]

    filtered = time_series.copy()
    filtered[mask] *= (target[mask] - target[mask].min() + 1)[..., np.newaxis]
    unfiltered = time_series.copy()

    mask_file = tmp_path / "mask.nii.gz"
    nib.nifti1.Nifti1Image(mask.astype(np.uint8), affine=np.eye(4)).to_filename(mask_file)
    inputnode.inputs.mask = mask_file
    unfiltered_inputnode.inputs.mask = mask_file

    filtered_file = tmp_path / "filtered.nii.gz"
    nib.nifti1.Nifti1Image(filtered, affine=np.eye(4)).to_filename(filtered_file)
    inputnode.inputs.bold = filtered_file

    unfiltered_file = tmp_path / "unfiltered.nii.gz"
    nib.nifti1.Nifti1Image(unfiltered, affine=np.eye(4)).to_filename(unfiltered_file)
    unfiltered_inputnode.inputs.bold = unfiltered_file

    graph = run_workflow(wf)

    (make_resultdicts,) = [n for n in graph.nodes if n.name == "make_resultdicts"]
    (resultdict,) = make_resultdicts.result.outputs.resultdicts
    falff_file = resultdict["images"]["falff"]

    falff = nib.nifti1.load(falff_file).get_fdata()
    np.testing.assert_allclose(falff, target, atol=1e-6)
