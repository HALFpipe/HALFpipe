# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import os
import shutil
from multiprocessing import cpu_count
from pathlib import Path

import pytest
from fmriprep import config

from halfpipe.logging import logger
from halfpipe.model.spec import Spec, save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph


@pytest.mark.timeout(120)
def test_empty(tmp_path: Path, mock_spec: Spec) -> None:
    mock_spec.settings = list()
    mock_spec.features = list()

    save_spec(mock_spec, workdir=tmp_path)

    with pytest.raises(RuntimeError):
        init_workflow(tmp_path)


@pytest.mark.timeout(600)
def test_with_reconall(tmp_path: Path, mock_spec: Spec) -> None:
    mock_spec.global_settings.update(dict(run_reconall=True))

    save_spec(mock_spec, workdir=tmp_path)

    workflow = init_workflow(tmp_path)

    graphs = init_execgraph(tmp_path, workflow)

    graph = next(iter(graphs.values()))
    assert any("recon" in u.name for u in graph.nodes)


def update_sidecar(path: Path, **metadata) -> None:
    with open(path, "r") as json_file:
        data = json.load(json_file)
    data.update(metadata)
    with open(path, "w") as json_file:
        json.dump(data, json_file)


@pytest.mark.parametrize(
    ("fieldmap_type", "with_runs", "b0_field_identifier"),
    [
        pytest.param("phasediff", False, False, id="phasediff-original"),
        pytest.param("epi", False, False, id="epi-original"),
        pytest.param("epi", True, False, id="epi-with-runs"),
        pytest.param("epi", False, True, id="epi-b0-field-identifier"),
    ],
)
def test_with_fieldmaps(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    with_runs: bool,
    fieldmap_type: str,
    b0_field_identifier: bool,
    mock_spec: Spec,
) -> None:
    bids_data = request.getfixturevalue("bids_data_with_runs" if with_runs else "bids_data")

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

    if b0_field_identifier:
        for path in fmap_path.glob("*_epi.json"):
            update_sidecar(path, B0FieldIdentifier=["pepolar_fmap_bold"])
        for path in (bids_path / "sub-1012" / "func").glob("*_bold.json"):
            update_sidecar(path, B0FieldSource=["pepolar_fmap_bold"])

    # Test creating the workflow
    workdir = tmp_path / "workdir"
    save_spec(mock_spec, workdir=workdir)

    config.nipype.omp_nthreads = cpu_count()

    workflow = init_workflow(workdir)

    if b0_field_identifier:
        b0_field_identifiers: set[str] = set()
        b0_field_sources: set[str] = set()
        for sidecar_path in (workdir / "rawdata").glob("sub-*/**/*.json"):
            with open(sidecar_path, "r") as json_file:
                sidecar = json.load(json_file)
            b0_field_identifiers.update(sidecar.get("B0FieldIdentifier", list()))
            b0_field_sources.update(sidecar.get("B0FieldSource", list()))
        assert b0_field_sources <= b0_field_identifiers, "All declared sources must be advertised by at least one field map"

    graphs = init_execgraph(workdir, workflow)
    graph = next(iter(graphs.values()))

    if fieldmap_type == "epi":
        assert any("topup" in u.fullname for u in graph.nodes), "Topup workflow missing"
    elif fieldmap_type == "phasediff":
        assert any("phdiff_wf" in u.fullname for u in graph.nodes), "Field map workflow missing"


@pytest.mark.parametrize(
    "bids_session_expanded_real_test_data",
    [1, 4],
    indirect=True,
    ids=["no_sessions", "four_sessions"],
)
def test_init_workflow_fibromyalgia(bids_session_expanded_real_test_data: tuple[Path, Path]) -> None:
    _, workdir_path = bids_session_expanded_real_test_data
    # Just check workflow can be created
    init_workflow(workdir_path)
