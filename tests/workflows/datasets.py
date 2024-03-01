# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import datalad.api as dl
from halfpipe.model.file.base import File
from halfpipe.model.file.schema import FileSchema


@dataclass
class Dataset:
    name: str
    url: str
    paths: list[str]


datasets: list[Dataset] = [
    Dataset(
        name="emory",  # multiband
        url="https://github.com/OpenNeuroDatasets/ds003540.git",
        paths=[
            "sub-01/anat/sub-01_T1w.nii.gz",
            "sub-01/func/sub-01_task-rest_acq-MB8_bold.nii.gz",
            "sub-01/func/sub-01_task-rest_acq-MB8_sbref.nii.gz",
        ],
    ),
    Dataset(
        name="on_harmony",  # single-band scan
        url="https://github.com/OpenNeuroDatasets/ds004712.git",
        paths=[
            "sub-13192/ses-NOT3GEM001/func/sub-13192_ses-NOT3GEM001_task-rest_acq-resopt2_bold.nii.gz",
            "sub-13192/ses-NOT3GEM001/anat/sub-13192_ses-NOT3GEM001_T1w.json",
            "sub-13192/ses-NOT3GEM001/anat/sub-13192_ses-NOT3GEM001_T1w.nii.gz",
        ],
    ),
    Dataset(
        name="adhd_200_neuroimage",  # 1.5 Tesla (old)
        url="https://datasets.datalad.org/adhd200/",
        paths=[
            "RawDataBIDS/NeuroIMAGE/sub-7446626/ses-1/anat/sub-7446626_ses-1_run-1_T1w.nii.gz",
            "RawDataBIDS/NeuroIMAGE/sub-7446626/ses-1/func/sub-7446626_ses-1_task-rest_run-1_bold.nii.gz",
            "RawDataBIDS/NeuroIMAGE/task-rest_bold.json",
            "RawDataBIDS/NeuroIMAGE/T1w.json",
        ],
    ),
    # missing one with fieldmaps
]


def download_dataset(tmp_path: Path, dataset: Dataset) -> File:
    ds = dl.install(source=dataset.url, path=str(tmp_path))

    for path in dataset.paths:
        with patch("datalad.log.log_progress"):
            ds.get(path)

    return FileSchema().load(dict(datatype="bids", path=str(tmp_path)))
