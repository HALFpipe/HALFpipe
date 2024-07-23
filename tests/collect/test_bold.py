# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import nibabel as nib
import numpy as np
from halfpipe.collect.bold import collect_bold_files
from halfpipe.ingest.database import Database
from halfpipe.model.file.base import File
from halfpipe.model.spec import Spec


@dataclass
class MockFactory:
    source_files: set[str]


def mock_fillmetadata(key, filepaths) -> bool:
    return True


def test_collect_bold_files(tmp_path: Path) -> None:
    image_path_a = str(tmp_path / "a.nii.gz")
    image_path_b = str(tmp_path / "b.nii.gz")
    image_path_t1w = str(tmp_path / "t1w.nii.gz")

    image = nib.nifti1.Nifti1Image(np.zeros((64, 64, 64, 3)), np.eye(4))
    nib.save(image, image_path_a)
    image = nib.nifti1.Nifti1Image(np.zeros((64, 64, 64, 2)), np.eye(4))
    nib.save(image, image_path_b)
    image = nib.nifti1.Nifti1Image(np.zeros((64, 64, 64)), np.eye(4))
    nib.save(image, image_path_t1w)

    post_processing_factory = MockFactory({image_path_a})
    feature_factory = MockFactory({image_path_b})

    empty_spec = Spec(datetime.now(), list())
    database = Database(empty_spec)
    database.fillmetadata = mock_fillmetadata  # type: ignore

    database.index(File(path=image_path_t1w, datatype="anat", suffix="T1w", tags=dict(sub="01"), extension=".nii.gz"))

    # Create a duplicate file
    func_file_base: dict[str, str] = dict(datatype="func", suffix="bold", extension=".nii.gz")
    database.index(File(path=image_path_a, **func_file_base, tags=dict(sub="01", task="rest")))
    database.index(File(path=image_path_b, **func_file_base, tags=dict(sub="01", task="rest")))

    bold_file_paths_dict: dict[str, list[str]] = collect_bold_files(database, post_processing_factory, feature_factory)  # type: ignore

    # Ensure that the duplicate was removed
    assert len(bold_file_paths_dict) == 1
    assert image_path_a in bold_file_paths_dict
