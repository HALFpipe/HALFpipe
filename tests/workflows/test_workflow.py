# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import logging
import os
import shutil
from multiprocessing import cpu_count
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest
from fmriprep import config
from templateflow.api import get as get_template

from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.ingest.spreadsheet import read_spreadsheet
from halfpipe.model.spec import save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph


@pytest.mark.timeout(120)
def test_empty(tmp_path, mock_spec):
    mock_spec.settings = list()
    mock_spec.features = list()

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


@pytest.mark.slow
@pytest.mark.timeout(3 * 3600)
def test_feature_extraction(tmp_path, mock_spec):
    """
    Test the feature extraction workflows.

    Parameters:
    - tmp_path: A fixture used to create a temporary directory.
    - mock_spec: A fixture providing a mock json.spec file.
    """

    # TODO why does this not print
    logging.getLogger("nipype.workflow").setLevel(logging.DEBUG)

    # Persist nipype cache across test runs
    # TODO remove this
    tmp_path = Path("/tmp/halfpipe")
    tmp_path.mkdir(exist_ok=True)

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

    (bold_path,) = tmp_path.glob("rawdata/sub-*/func/*_bold.nii.gz")
    bold_image = nib.nifti1.load(bold_path)

    run_stage_run(opts)

    template_path = get_template("MNI152NLin2009cAsym", resolution=2, desc="brain", suffix="T1w")
    template_image = nib.nifti1.load(template_path)
    assert bold_image.shape[:3] != template_image.shape  # This should always pass

    (native_reference_path,) = tmp_path.glob("derivatives/fmriprep/sub-*/func/*_space-T1w_boldref.nii.gz")
    native_reference_image = nib.nifti1.load(native_reference_path)

    reference_images = dict(standard=template_image, native=native_reference_image)

    for space in {"standard", "native"}:
        (preproc_path,) = tmp_path.glob(f"derivatives/halfpipe/sub-*/func/*setting-{space}*_bold.nii.gz")
        preproc_image = nib.nifti1.load(preproc_path)
        assert bold_image.shape[3] == preproc_image.shape[3] + dummy_scans

        assert preproc_image.shape[:3] == reference_images[space].shape
        np.testing.assert_allclose(preproc_image.affine, reference_images[space].affine)

        if space == "native":
            target_zooms = bold_image.header.get_zooms()
        elif space == "standard":
            target_zooms = (
                *reference_images[space].header.get_zooms()[:3],
                bold_image.header.get_zooms()[3],
            )
        else:
            raise ValueError(f"Unknown space: {space}")
        np.testing.assert_allclose(preproc_image.header.get_zooms(), target_zooms)

        (confounds_path,) = tmp_path.glob(f"derivatives/halfpipe/sub-*/func/*setting-{space}*_desc-confounds_regressors.tsv")
        confounds_frame = read_spreadsheet(confounds_path)
        assert bold_image.shape[3] == confounds_frame.shape[0] + dummy_scans

        for path in tmp_path.glob(f"derivatives/halfpipe/sub-*/func/task-*/*feature-{space}*.nii.gz"):
            image = nib.nifti1.load(path)
            assert image.shape[:3] == reference_images[space].shape
            np.testing.assert_allclose(image.affine, reference_images[space].affine)


def test_with_fieldmaps(tmp_path, bids_data, mock_spec):
    # TODO: Create an assertion that checks that field maps are used

    bids_path = tmp_path / "bids"
    shutil.copytree(bids_data, bids_path)

    # delete extra files
    fmap_path = bids_path / "sub-1012" / "fmap"
    files = [
        "sub-1012_acq-3mm_phasediff.nii.gz",
        "sub-1012_acq-3mm_phasediff.json",
        "sub-1012_acq-3mm_magnitude2.nii.gz",
        "sub-1012_acq-3mm_magnitude2.json",
        "sub-1012_acq-3mm_magnitude1.nii.gz",
        "sub-1012_acq-3mm_magnitude1.json",
    ]
    for i in files:
        Path(fmap_path / i).unlink()

    # copy image file
    shutil.copy(
        os.path.join(fmap_path, "sub-1012_dir-PA_epi.nii.gz"),
        os.path.join(fmap_path, "sub-1012_dir-AP_epi.nii.gz"),
    )

    # copy metadata
    with open(fmap_path / "sub-1012_dir-PA_epi.json", "r") as json_file:
        data = json.load(json_file)
    data["PhaseEncodingDirection"] = "j-"
    with open(fmap_path / "sub-1012_dir-AP_epi.json", "w") as json_file:
        json.dump(data, json_file)

    # start testing
    workdir = tmp_path / "workdir"
    save_spec(mock_spec, workdir=workdir)

    config.nipype.omp_nthreads = cpu_count()

    workflow = init_workflow(workdir)

    graphs = init_execgraph(workdir, workflow)
    graph = next(iter(graphs.values()))

    assert any("fmap_select" in u.fullname for u in graph.nodes), "Field map workflow missing"
