# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from dataclasses import dataclass
from pathlib import Path

import datalad.api as dl
from halfpipe.model.file.base import File
from halfpipe.model.file.schema import FileSchema


@dataclass
class Dataset:
    name: str
    url: str
    paths: list[str]

    def download(self, tmp_path: Path) -> File:
        ds = dl.clone(source=self.url, path=str(tmp_path))
        for path in self.paths:
            ds.get(path)
        return FileSchema().load(dict(datatype="bids", path=str(tmp_path)))


datasets: list[Dataset] = [
    # Dataset(
    #     name="on_harmony",  # single-band scan
    #     openneuro_id="ds004712",
    #     # url="https://github.com/OpenNeuroDatasets/ds004712.git",
    #     url="https://github.com/OpenNeuroDatasets/ds004712/blob/master",
    #     paths=[
    #         "sub-13192/ses-NOT3GEM001/func/sub-13192_ses-NOT3GEM001_task-rest_acq-resopt2_bold.nii.gz",
    #         "sub-13192/ses-NOT3GEM001/anat/sub-13192_ses-NOT3GEM001_T1w.json",
    #         "sub-13192/ses-NOT3GEM001/anat/sub-13192_ses-NOT3GEM001_T1w.nii.gz",
    #     ],
    # ),
    # Dataset(
    #     name="emory",  # multiband
    #     openneuro_id="ds003540",
    #     url="https://github.com/OpenNeuroDatasets/ds003540/blob/master",
    #     # url="https://github.com/OpenNeuroDatasets/ds003540.git",
    #     paths=[
    #         "sub-01/anat/sub-01_T1w.nii.gz",
    #         "sub-01/func/sub-01_task-rest_acq-MB8_bold.nii.gz",
    #         "sub-01/func/sub-01_task-rest_acq-MB8_sbref.nii.gz",
    #     ],
    # ),
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
    # # this dataset is missing datasetDOI field and openneuro cannot handle it
    # Dataset(
    #     name="fmap_sequences",  # Has fieldmaps
    #     openneuro_id="ds001600",
    #     # url="https://github.com/OpenNeuroDatasets/ds001600/blob/master",
    #     url="https://github.com/OpenNeuroDatasets/ds001600.git",
    #     paths=[
    #         "sub-1/fmap/sub-1_dir-PA_epi.nii.gz",
    #         "sub-1/fmap/sub-1_dir-PA_epi.json",
    #         "sub-1/fmap/sub-1_dir-AP_epi.nii.gz",
    #         "sub-1/fmap/sub-1_dir-AP_epi.json",
    #         "sub-1/func/sub-1_task-rest_acq-AP_bold.json",
    #         "sub-1/func/sub-1_task-rest_acq-AP_bold.nii.gz",
    #     ],
    # ),
]


# def download_dataset(tmp_path: Path, dataset: Dataset) -> File:
#     # Download each specified file into the dataset-specific directory
#     for file_path in dataset.paths:
#         on.download(dataset=dataset.openneuro_id, include=file_path, target_dir=tmp_path)
#     return FileSchema().load(dict(datatype="bids", path=str(tmp_path)))


#! Datalad function with install

# def download_dataset(tmp_path: Path, dataset: Dataset) -> File:
#     ds = dl.install(source=dataset.url, path=str(tmp_path))
#     for path in dataset.paths:
#         with patch("datalad.log.log_progress"):
#             ds.get(path)
#     return FileSchema().load(dict(datatype="bids", path=str(tmp_path)))

#! Datalad function with clone


#! This function uses requests works but does not copy bids structure

# def download_dataset(tmp_path: Path, dataset: Dataset) -> File:
#     for path in dataset.paths:
#         # Construct the full URL for each file
#         file_url = f"{dataset.url}/{path}"
#         local_file_path = tmp_path / Path(path).name
#         response = requests.get(file_url)
#         response.raise_for_status()  # Will raise an HTTPError if the request returned an unsuccessful status code
#         # Write the content to the file
#         with open(local_file_path, "wb") as file:
#             file.write(response.content)
#     return FileSchema().load(dict(datatype="bids", path=str(tmp_path)))
