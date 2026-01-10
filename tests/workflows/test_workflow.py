# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import os
import shutil
from multiprocessing import cpu_count
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest
import scipy.spatial.distance
from fmriprep import config
from templateflow.api import get as get_template

from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.ingest.spreadsheet import read_spreadsheet
from halfpipe.logging import logger
from halfpipe.model.spec import Spec, save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph


@pytest.mark.timeout(120)
def test_empty(tmp_path, mock_spec):
    mock_spec.settings = list()
    mock_spec.features = list()
    mock_spec.downstream_features = list()

    save_spec(mock_spec, workdir=tmp_path)

    with pytest.raises(RuntimeError):
        init_workflow(tmp_path)


@pytest.mark.timeout(600)
def test_with_reconall(tmp_path, mock_spec):
    mock_spec.global_settings.update(dict(run_reconall=True))

    save_spec(mock_spec, workdir=tmp_path)

    workflow = init_workflow(tmp_path)

    graphs = init_execgraph(tmp_path, workflow)

    graph = next(iter(graphs.values()))
    assert any("recon" in u.name for u in graph.nodes)


def dice_similarity(
    path_or_image: Path | nib.nifti1.Nifti1Image,
    reference_mask_path_or_image: Path | nib.nifti1.Nifti1Image,
    threshold: float = 0.0,
) -> float:
    image = nib.nifti1.load(path_or_image) if isinstance(path_or_image, Path) else path_or_image
    data = image.get_fdata()
    mask = np.logical_and(data > threshold, np.logical_not(np.isclose(data, threshold)))
    if mask.ndim == 4:
        mask = np.any(mask, axis=3)
    reference_mask_image = (
        nib.nifti1.load(reference_mask_path_or_image)
        if isinstance(reference_mask_path_or_image, Path)
        else reference_mask_path_or_image
    )
    reference_mask = np.asanyarray(reference_mask_image.dataobj, dtype=bool)
    assert image.shape[:3] == reference_mask_image.shape, "Images have different shapes"
    assert np.allclose(image.affine, reference_mask_image.affine, atol=1e-3), "Images have different affines"
    np.testing.assert_allclose(image.header.get_zooms()[:3], reference_mask_image.header.get_zooms())
    dissimilarity = scipy.spatial.distance.dice(mask.flatten(), reference_mask.flatten())
    return 1.0 - dissimilarity


@pytest.mark.slow
@pytest.mark.timeout(3 * 3600)
def test_feature_extraction(tmp_path: Path, mock_spec: Spec) -> None:
    """
    Test the feature extraction workflows.

    Parameters:
    - tmp_path: A fixture used to create a temporary directory.
    - mock_spec: A fixture providing a mock json.spec file.
    """

    template_mask_path = get_template("MNI152NLin2009cAsym", resolution=2, desc="brain", suffix="mask")
    template_mask_image = nib.nifti1.load(template_mask_path)

    dummy_scans = 3
    mock_spec.global_settings.update(dict(dummy_scans=dummy_scans))

    save_spec(mock_spec, workdir=tmp_path)

    config.nipype.omp_nthreads = cpu_count()

    workflow = init_workflow(tmp_path)

    graphs = init_execgraph(tmp_path, workflow)
    graph = next(iter(graphs.values()))

    # Ensure key workflows exist
    assert any("anat_fit_wf" in u.fullname for u in graph.nodes), "Anat workflow missing"
    assert any("bold_fit_wf" in u.fullname for u in graph.nodes), "Bold workflow missing"

    parser = build_parser()
    opts = parser.parse_args(args=list())

    opts.graphs = graphs
    opts.nipype_run_plugin = "Simple"
    opts.debug = True

    bold_path = tmp_path / "rawdata" / "sub-1012" / "func" / "sub-1012_task-rest_bold.nii.gz"
    bold_image = nib.nifti1.load(bold_path)
    assert bold_image.shape[:3] != template_mask_image.shape, "Input image is already in standard space"

    run_stage_run(opts)

    fmriprep_func_derivatives_path = tmp_path / "derivatives" / "fmriprep" / "sub-1012" / "func"
    native_reference_mask_image_path = fmriprep_func_derivatives_path / "sub-1012_task-rest_space-T1w_desc-brain_mask.nii.gz"
    native_reference_mask_image = nib.nifti1.load(native_reference_mask_image_path)
    reference_mask_images = dict(standard=template_mask_image, native=native_reference_mask_image)

    func_derivatives_path = tmp_path / "derivatives" / "halfpipe" / "sub-1012" / "func"
    for space in {"standard", "native"}:
        (preproc_path,) = func_derivatives_path.glob(f"sub-1012_task-rest_setting-{space}*_bold.nii.gz")
        preproc_image = nib.nifti1.load(preproc_path)
        assert bold_image.shape[3] == preproc_image.shape[3] + dummy_scans, "Dummy scans were not removed"

        assert dice_similarity(preproc_image, reference_mask_images[space]) >= 0.9

        if space == "native":
            target_zooms = bold_image.header.get_zooms()
        elif space == "standard":
            target_zooms = (
                *reference_mask_images[space].header.get_zooms()[:3],
                bold_image.header.get_zooms()[3],
            )
        else:
            raise ValueError(f"Unknown space: {space}")
        np.testing.assert_allclose(preproc_image.header.get_zooms(), target_zooms)

        (confounds_path,) = func_derivatives_path.glob(f"sub-1012_task-rest_setting-{space}*_desc-confounds_regressors.tsv")
        confounds_frame = read_spreadsheet(confounds_path)
        assert bold_image.shape[3] == confounds_frame.shape[0] + dummy_scans

        for path in func_derivatives_path.glob(f"task-rest/sub-1012_task-rest_feature-{space}*.nii.gz"):
            tokens = path.name.removesuffix(".nii.gz").split("_")
            if tokens[-1] == "mask":
                suffix = "mask"
            elif tokens[-1] == "statmap":
                suffix = tokens[-2]
            else:
                suffix = None
            if suffix in {"mask", "stat-variance", "stat-sigmasquareds"}:
                threshold = 0.9
            else:
                threshold = 0.0
            assert dice_similarity(path, reference_mask_images[space]) >= threshold, f"Low dice similarity for {path.name}"

    fmripost_aroma_template_mask_path = get_template("MNI152NLin6Asym", resolution=2, desc="brain", suffix="mask")
    fmripost_aroma_components_path = (
        tmp_path
        / "derivatives"
        / "fmripost_aroma"
        / "sub-1012"
        / "func"
        / "sub-1012_task-rest_thresh-0p5_desc-melodic_components.nii.gz"
    )
    assert dice_similarity(fmripost_aroma_components_path, fmripost_aroma_template_mask_path) >= 0.9

    tsnr_image_path = (
        tmp_path / "derivatives" / "halfpipe" / "sub-1012" / "func" / "sub-1012_task-rest_stat-tsnr_boldmap.nii.gz"
    )
    assert dice_similarity(tsnr_image_path, template_mask_path, threshold=20.0) >= 0.8


@pytest.mark.parametrize("fieldmap_type", ["phasediff", "epi"])
def test_with_fieldmaps(tmp_path: Path, bids_data: Path, mock_spec: Spec, fieldmap_type: str) -> None:
    bids_path = tmp_path / "bids"
    shutil.copytree(bids_data, bids_path)

    shutil.rmtree(bids_path / "sub-1012" / "dwi")
    (bids_path / "sub-1012" / "sub-1012_scans.tsv").unlink()

    for file in mock_spec.files:
        if file.datatype == "bids":
            file.path = str(bids_path)

    fmap_path = bids_path / "sub-1012" / "fmap"

    phasediff_files = [
        "sub-1012_acq-3mm_phasediff.nii.gz",
        "sub-1012_acq-3mm_phasediff.json",
        "sub-1012_acq-3mm_magnitude2.nii.gz",
        "sub-1012_acq-3mm_magnitude2.json",
        "sub-1012_acq-3mm_magnitude1.nii.gz",
        "sub-1012_acq-3mm_magnitude1.json",
    ]

    if fieldmap_type == "phasediff":
        for path in fmap_path.glob("*.nii.gz"):
            if path.name not in phasediff_files:
                logger.info(f"Removing unused fieldmap file: {path}")
                path.unlink()
    elif fieldmap_type == "epi":
        # Create fake image for the opposite phase encoding direction
        shutil.copy(
            os.path.join(fmap_path, "sub-1012_dir-PA_epi.nii.gz"),
            os.path.join(fmap_path, "sub-1012_dir-AP_epi.nii.gz"),
        )
        with open(fmap_path / "sub-1012_dir-PA_epi.json", "r") as json_file:
            data = json.load(json_file)
        data["PhaseEncodingDirection"] = "j-"
        with open(fmap_path / "sub-1012_dir-AP_epi.json", "w") as json_file:
            json.dump(data, json_file)

        for phasediff_file in phasediff_files:
            path = fmap_path / phasediff_file
            if path.exists():
                logger.info(f"Removing unused fieldmap file: {path}")
                path.unlink()
    else:
        raise ValueError(f"Unknown fieldmap type: {fieldmap_type}")

    # Test creating the workflow
    workdir = tmp_path / "workdir"
    save_spec(mock_spec, workdir=workdir)

    config.nipype.omp_nthreads = cpu_count()

    workflow = init_workflow(workdir)

    graphs = init_execgraph(workdir, workflow)
    graph = next(iter(graphs.values()))

    if fieldmap_type == "epi":
        assert any("topup" in u.fullname for u in graph.nodes), "Topup workflow missing"
    elif fieldmap_type == "phasediff":
        assert any("phdiff_wf" in u.fullname for u in graph.nodes), "Field map workflow missing"
