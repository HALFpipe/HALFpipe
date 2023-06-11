# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from unittest import TestCase

from halfpipe.file_index.bids import BIDSIndex
from halfpipe.result.base import ResultDict
from halfpipe.result.bids.images import load_images, save_images


def test_images(tmp_path: Path):
    statmap_path = tmp_path / "statmap.nii.gz"
    with statmap_path.open("w") as file_handle:
        file_handle.write("test")  # File cannot be empty, because we skip empty files

    result: ResultDict = {
        "tags": {
            "task": "faces",
            "feature": "taskBased1",
            "taskcontrast": "facesGtScrambled",
            "run": "07",
            "sub": "01",
        },
        "images": {
            "variance": statmap_path,
            "effect": statmap_path,
            "mask": statmap_path,
            "dof": statmap_path,
            "z": statmap_path,
        },
        "vals": {
            "dummy_scans": 0,
        },
        "metadata": {
            "acquisition_orientation": "LAS",
        },
    }

    save_images([result], tmp_path)

    index = BIDSIndex()
    index.put(tmp_path / "derivatives" / "halfpipe")

    (actual,) = load_images(index)

    test_case = TestCase()
    test_case.maxDiff = None

    test_case.assertDictEqual(result["tags"], actual["tags"])
    test_case.assertDictEqual(result["vals"], actual["vals"])
    test_case.assertDictEqual(result["metadata"], actual["metadata"])
    assert result["images"].keys() == actual["images"].keys()
