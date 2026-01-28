# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import os
import shutil
import tarfile
import tempfile

# from halfpipe.logging.context import Context, setup as setup_logging
from math import inf
from pathlib import Path
from random import choices, normalvariate, seed
from zipfile import ZipFile

import nibabel as nib
import pandas as pd
import pytest
from nilearn.image import new_img_like

from halfpipe.ingest.database import Database
from halfpipe.logging import logger
from halfpipe.model.feature import FeatureSchema
from halfpipe.model.file.base import File
from halfpipe.model.file.schema import FileSchema
from halfpipe.model.model import ModelSchema
from halfpipe.model.spec import Spec, SpecSchema, save_spec
from halfpipe.resource import get as get_resource
from halfpipe.utils.image import nvol

from ..create_mock_bids_dataset import create_bids_data
from ..resource import setup as setup_test_resources
from .datasets import Dataset
from .expand_bids_dataset import expand_bids_dataset
from .spec import TestSetting, make_bids_only_spec, make_spec


@pytest.fixture(scope="session")
def bids_data(tmp_path_factory, request) -> Path:
    # --------------------------------------------------------------
    # Read parameters from test (default = False)
    # --------------------------------------------------------------
    extend_tasks = False
    if hasattr(request, "param"):
        if isinstance(request.param, dict):
            extend_tasks = request.param.get("extend_tasks", False)
        else:
            extend_tasks = bool(request.param)

    tmp_path = tmp_path_factory.mktemp(basename="bids_data")
    os.chdir(str(tmp_path))

    setup_test_resources()
    input_path = get_resource("bids_data.zip")

    with ZipFile(input_path) as fp:
        fp.extractall(tmp_path)

    bids_data_path = tmp_path / "bids_data"
    func_path = bids_data_path / "sub-1012" / "func"
    fmap_path = bids_data_path / "sub-1012" / "fmap"

    # --------------------------------------------------------------
    # Original behavior (always runs)
    # --------------------------------------------------------------
    events_file = func_path / "sub-1012_task-rest_events.tsv"
    events_file.unlink()

    bold_file = func_path / "sub-1012_task-rest_bold.nii.gz"
    bold_img = nib.load(bold_file)
    bold_data = bold_img.get_fdata()[..., :64]
    bold_img = new_img_like(bold_img, bold_data, copy_header=True)
    nib.save(bold_img, bold_file)

    # Explicit IntendedFor always starts with rest
    intended_for = ["func/sub-1012_task-rest_bold.nii.gz"]

    # --------------------------------------------------------------
    # Optional extension controlled by parametrization
    # --------------------------------------------------------------
    if extend_tasks:
        task_runs = {
            "task1": [1, 2],
            "task2": [1],
        }

        src_prefix = "sub-1012_task-rest_bold"

        for task, runs in task_runs.items():
            for run in runs:
                run_label = f"run-{run:02d}"
                task_label = f"task-{task}_{run_label}"
                dst_prefix = f"sub-1012_{task_label}_bold"

                # Copy NIfTI
                shutil.copy(
                    func_path / f"{src_prefix}.nii.gz",
                    func_path / f"{dst_prefix}.nii.gz",
                )

                # Copy JSON
                shutil.copy(
                    func_path / f"{src_prefix}.json",
                    func_path / f"{dst_prefix}.json",
                )

                # Create run-specific events file
                (func_path / f"sub-1012_{task_label}_events.tsv").write_text("onset\tduration\n0\t10\n")

                # Explicit IntendedFor entry
                intended_for.append(f"func/{dst_prefix}.nii.gz")

    # --------------------------------------------------------------
    # Write IntendedFor explicitly to all fmap JSONs
    # --------------------------------------------------------------
    for fmap_json in fmap_path.glob("*.json"):
        with fmap_json.open() as f:
            data = json.load(f)

        data["IntendedFor"] = intended_for

        with fmap_json.open("w") as f:
            json.dump(data, f, indent=2)

    return bids_data_path


@pytest.fixture(scope="session")
def mock_task_events(tmp_path_factory, bids_data) -> File:
    tmp_path = tmp_path_factory.mktemp(basename="task_events")

    os.chdir(str(tmp_path))

    seed(a=0x5E6128C4)

    spec_schema = SpecSchema()
    spec = spec_schema.load(spec_schema.dump({}), partial=True)
    assert isinstance(spec, Spec)

    spec.files = list(
        map(
            FileSchema().load,
            [
                dict(datatype="bids", path=str(bids_data)),
            ],
        )
    )

    database = Database(spec)

    bold_file_paths = database.get(datatype="func", suffix="bold")
    assert database.fillmetadata("repetition_time", bold_file_paths)

    scan_duration = inf
    for b in bold_file_paths:
        repetition_time = database.metadata(b, "repetition_time")
        assert isinstance(repetition_time, float)
        scan_duration = min(nvol(b) * repetition_time, scan_duration)

    onset = []
    duration = []

    t = 0.0
    d = 5.0
    while True:
        t += d
        t += abs(normalvariate(0, 1)) + 1.0  # jitter

        if t < scan_duration:
            onset.append(t)
            duration.append(d)
        else:
            break

    n = len(duration)
    trial_type = choices(["a", "b"], k=n)

    events = pd.DataFrame(dict(onset=onset, duration=duration, trial_type=trial_type))

    events_fname = Path.cwd() / "events.tsv"
    events.to_csv(events_fname, sep="\t", index=False, header=True)

    return FileSchema().load(
        dict(
            datatype="func",
            suffix="events",
            extension=".tsv",
            tags=dict(task="rest"),
            path=str(events_fname),
            metadata=dict(units="seconds"),
        )
    )


@pytest.fixture(scope="session")
def atlas_harvard_oxford(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    tmp_path = tmp_path_factory.mktemp(basename="pcc_mask")

    os.chdir(str(tmp_path))
    setup_test_resources()

    inputtarpath = get_resource("HarvardOxford.tgz")

    with tarfile.open(inputtarpath) as fp:
        fp.extractall(tmp_path)

    maps = {
        m: (tmp_path / "data" / "atlases" / "HarvardOxford" / f"HarvardOxford-{m}.nii.gz")
        for m in ("cort-prob-1mm", "cort-prob-2mm", "sub-prob-1mm", "sub-prob-2mm")
    }
    return maps


@pytest.fixture(scope="session")
def pcc_mask(tmp_path_factory: pytest.TempPathFactory, atlas_harvard_oxford: dict[str, Path]) -> Path:
    tmp_path = tmp_path_factory.mktemp(basename="pcc_mask")

    os.chdir(str(tmp_path))

    atlas_img = nib.nifti1.load(atlas_harvard_oxford["cort-prob-2mm"])
    atlas = atlas_img.get_fdata()

    pcc_mask = atlas[..., 29] > 10

    pcc_mask_img = new_img_like(atlas_img, pcc_mask, copy_header=True)

    pcc_mask_fname = Path.cwd() / "pcc.nii.gz"
    nib.loadsave.save(pcc_mask_img, pcc_mask_fname)

    return pcc_mask_fname


@pytest.fixture(scope="function")
def mock_spec(bids_data: Path, mock_task_events: File, pcc_mask: Path) -> Spec:
    bids_file = FileSchema().load(
        dict(datatype="bids", path=str(bids_data)),
    )

    base_setting = dict(
        confounds_removal=["(trans|rot)_[xyz]"],
        grand_mean_scaling=dict(mean=10000.0),
        ica_aroma=True,
    )
    test_settings = [
        TestSetting(
            name="standard",
            base_setting=dict(space="standard", **base_setting),
        ),
        TestSetting(
            name="native",
            base_setting=dict(space="native", **base_setting),
        ),
    ]

    return make_spec(dataset_files=[bids_file], pcc_mask=pcc_mask, test_settings=test_settings, event_file=mock_task_events)


@pytest.fixture(scope="session")
def bids_session_test_empty_mock_data(request):
    """
    Create a parallel-safe temporary BIDS hierarchy with optional number of sessions + workdir.

    - Accepts sessions via request.param
    - Cleans up after the test
    """
    sessions = getattr(request, "param", [])

    # Use a unique temporary directory (parallel-safe)
    base_path = Path(tempfile.mkdtemp(prefix="bids_test_"))
    bids_label = "multisession-bids"
    data_path = base_path / bids_label
    workdir_path = base_path / "workdir"
    data_path.mkdir(parents=True, exist_ok=True)
    workdir_path.mkdir(parents=True, exist_ok=True)

    # Example BIDS setup
    number_of_subjects = 3
    tasks_conditions_dict = {
        "anticipation_acq-seq": ["cue_negative", "cue_neutral", "img_negative", "img_neutral"],
        "workingmemory_acq-seq": ["active_change", "active_nochange", "passive"],
        "restingstate-mb3": [],
    }

    create_bids_data(
        data_path,
        number_of_subjects=number_of_subjects,
        tasks_conditions_dict=tasks_conditions_dict,
        field_maps=True,
        sessions=sessions,
    )

    bids_file = FileSchema().load(dict(datatype="bids", path=str(data_path)))

    mock_spec = make_bids_only_spec(dataset_files=[bids_file])
    preproc_setting = {
        "space": "standard",
        "name": "preproc",
        "filters": [{"type": "tag", "action": "include", "entity": "task", "values": ["workingmemory"]}],
        "output_image": True,
    }
    mock_spec.settings.append(preproc_setting)
    save_spec(mock_spec, workdir=workdir_path)

    # Yield paths to the test
    yield data_path, workdir_path

    # Cleanup after the test
    shutil.rmtree(base_path)


@pytest.fixture(scope="session")
def fibromyalgia_base_dataset(tmp_path_factory):
    """
    Download the OpenNeuro dataset exactly once per test session.
    """
    base_path = tmp_path_factory.mktemp("openneuro_cache")
    base_dataset_path = base_path / "ds004144"

    if not base_dataset_path.exists():
        dataset = Dataset(
            name="fibromyalgia",
            openneuro_id="ds004144",
            openneuro_url="https://openneuro.org/datasets/ds004144/versions/1.0.2",
            url="https://github.com/OpenNeuroDatasets/ds004144.git",
            paths=[
                "sub-002/anat/sub-002_T1w.nii.gz",
                "sub-002/anat/sub-002_T1w.json",
                "sub-002/func/sub-002_task-epr_bold.nii.gz",
                "sub-002/func/sub-002_task-epr_bold.json",
                "sub-002/func/sub-002_task-epr_events.tsv",
                "sub-002/func/sub-002_task-rest_bold.nii.gz",
                "sub-002/func/sub-002_task-rest_bold.json",
            ],
        )
        dataset.download(base_dataset_path)
    logger.info(f"fibromyalgia dataset path: {base_dataset_path}")

    return base_dataset_path


@pytest.fixture(scope="session")
def fixed_tmp_path() -> Path:
    path = Path("/tmp/atlases_and_maps/")
    path.mkdir(parents=True, exist_ok=True)  # Ensure the path exists
    return path


@pytest.fixture(scope="session")
def bids_session_expanded_real_test_data(
    request, fibromyalgia_base_dataset, tmp_path_factory, atlases_maps_seed_images_path, covariant_spreadsheet_path
):
    from typing import cast

    sessions = int(cast(int, getattr(request, "param", 0)))

    seed_image_file_pattern = atlases_maps_seed_images_path / "{seed}_seed_2009.nii.gz"

    base_path = tmp_path_factory.mktemp("bids_test")
    bids_label = "multisession-bids"
    data_path = base_path / bids_label
    workdir_path = base_path / "workdir"
    data_path.mkdir(parents=True)
    workdir_path.mkdir(parents=True)
    logger.info(f"bids path: {data_path}")
    logger.info(f"workdir path: {workdir_path}")

    expand_bids_dataset(
        base_dataset_dir=fibromyalgia_base_dataset,
        output_dataset_dir=data_path,
        base_subject="sub-002",
        n_subjects=3,
        n_sessions=sessions,
    )

    bids_file = FileSchema().load(dict(datatype="bids", path=str(data_path)))
    logger.info(f"Covariant spreadsheet path: {covariant_spreadsheet_path}")
    mock_spec = make_bids_only_spec(dataset_files=[bids_file])
    file_schema = FileSchema()

    spreadsheet_metadata = {
        "variables": [
            {"name": "IDs", "type": "id"},
            {"name": "Case", "type": "continuous"},
            {"name": "Age", "type": "continuous"},
            {"name": "Sex", "type": "categorical", "levels": ["0", "1"]},
            {"name": "Site", "type": "categorical", "levels": ["1", "2", "3"]},
            {"name": "Severity", "type": "continuous"},
        ]
    }

    covariant_spreadsheet_file_obj = file_schema.load(
        dict(path=str(covariant_spreadsheet_path), datatype="spreadsheet", metadata=spreadsheet_metadata)
    )
    mock_spec.files.append(covariant_spreadsheet_file_obj)

    seed_file_obj = file_schema.load(
        dict(path=str(seed_image_file_pattern), datatype="ref", suffix="seed", extension=".nii.gz", tags={}, metadata=dict())
    )

    mock_spec.files.append(seed_file_obj)

    # make one preproc 'feature'
    mock_spec.settings.append(
        {
            "space": "standard",
            "name": "preproc",
            "filters": [
                {
                    "type": "tag",
                    "action": "include",
                    "entity": "task",
                    "values": ["epr"],
                }
            ],
            "output_image": True,
        }
    )
    mock_spec.settings.append(
        {
            "space": "standard",
            "ica_aroma": False,
            "grand_mean_scaling": {"mean": 10000.0},
            "name": "seedCorrSetting",
            "filters": [],
            "output_image": False,
        }
    )

    feature_schema = FeatureSchema()

    test_seed_based_feature = feature_schema.load(
        dict(
            name="seedCorr",
            setting="seedCorrSetting",
            type="seed_based_connectivity",
            seeds=[],
            # seeds= [
            #     "R_vlPFC_pt"
            # ],
            min_seed_coverage=0.8,
        )
    )
    mock_spec.features.append(test_seed_based_feature)

    model_schema = ModelSchema()
    test_lm_model = model_schema.load(
        dict(
            name="model",
            inputs=["seedCorr"],
            filters=[{"type": "missing", "action": "exclude", "variable": "Case"}],
            type="lme",
            across="sub",
            algorithms=["flame1", "mcartest", "heterogeneity"],
            spreadsheet=str(covariant_spreadsheet_path),
            contrasts=[{"type": "infer", "variable": ["Case"]}],
        )
    )
    mock_spec.models.append(test_lm_model)

    save_spec(mock_spec, workdir=workdir_path)

    yield data_path, workdir_path
