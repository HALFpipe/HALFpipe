# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import subprocess
import tarfile
from math import inf
from pathlib import Path
from random import choices, normalvariate, seed
from zipfile import ZipFile

import nibabel as nib
import pandas as pd
import pytest
from halfpipe.ingest.database import Database
from halfpipe.model.file.base import File
from halfpipe.model.file.schema import FileSchema
from halfpipe.model.spec import Spec, SpecSchema
from halfpipe.resource import get as get_resource
from halfpipe.utils.image import nvol
from nilearn.image import new_img_like

from ..resource import setup as setup_test_resources
from .datasets import datasets, download_dataset
from .spec import make_spec


@pytest.fixture(scope="package")
def bids_data(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="bids_data")

    os.chdir(str(tmp_path))

    setup_test_resources()
    input_path = get_resource("bids_data.zip")

    with ZipFile(input_path) as fp:
        fp.extractall(tmp_path)

    bids_data_path = tmp_path / "bids_data"

    func_path = bids_data_path / "sub-1012" / "func"

    Path(func_path / "sub-1012_task-rest_events.tsv").unlink()  # this file is empty

    bold_file = func_path / "sub-1012_task-rest_bold.nii.gz"
    bold_img = nib.nifti1.load(bold_file)
    bold_data = bold_img.get_fdata()[..., :64]  # we don't need so many volumes for testing
    bold_img = new_img_like(bold_img, bold_data, copy_header=True)
    nib.loadsave.save(bold_img, bold_file)

    return bids_data_path


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def atlas_harvard_oxford(tmp_path_factory) -> dict[str, Path]:
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


@pytest.fixture(scope="module")
def pcc_mask(tmp_path_factory, atlas_harvard_oxford: dict[str, Path]) -> Path:
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
    return make_spec(
        dataset_files=[bids_file],
        pcc_mask=pcc_mask,
        event_file=mock_task_events,
    )


@pytest.fixture(scope="session")
def consistency_datasets(tmp_path_factory):
    dataset_root_paths = []

    for dataset in datasets:
        dataset_tmp_path = tmp_path_factory.mktemp(f"consistency_data_{dataset.name}")
        os.chdir(str(dataset_tmp_path))
        # Set git credentials because datalad uses git commands that sometimes need config info: https://github.com/datalad/datalad/issues/2272
        subprocess.run(["git", "config", "--global", "user.email", "datalad-user@example.com"])
        subprocess.run(["git", "config", "--global", "user.name", "DataLad User"])

        downloaded_dataset = download_dataset(dataset_tmp_path, dataset)
        assert Path(downloaded_dataset.path).exists(), f"Dataset directory {downloaded_dataset.path} does not exist"

        # Add the root path of the downloaded dataset
        dataset_root_paths.append(dataset_tmp_path)

    return dataset_root_paths


@pytest.fixture(scope="function", params=datasets)
def consistency_spec(request, consistency_datasets, pcc_mask: Path):
    dataset_root_path = consistency_datasets[datasets.index(request.param)]  # Retrieve the root path for the current datase
    dataset_file = FileSchema().load(
        dict(datatype="bids", path=str(dataset_root_path)),
    )

    return make_spec(
        dataset_files=[dataset_file],
        pcc_mask=pcc_mask,
    )
