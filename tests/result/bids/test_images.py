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

    extra: ResultDict = {
        "vals": {
            "dummy_scans": 0,
        },
        "metadata": {
            "acquisition_orientation": "LAS",
        },
    }
    result1: ResultDict = {
        "tags": {
            "task": "faces",
            "run": "07",
            "sub": "01",
        },
        "images": {
            "tsnr": statmap_path,
        },
        **extra,
    }
    result2: ResultDict = {
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
        **extra,
    }
    results = [result1, result2]

    save_images(results, tmp_path)
    derivatives_path = tmp_path / "derivatives" / "halfpipe"

    assert (derivatives_path / "sub-01" / "func" / "sub-01_task-faces_run-07_stat-tsnr_boldmap.nii.gz").is_file()

    index = BIDSIndex()
    index.put(derivatives_path)

    loaded_results = load_images(index)
    assert len(loaded_results) == 2

    loaded_result1: ResultDict | None = None
    loaded_result2: ResultDict | None = None
    for loaded_result in loaded_results:
        if "taskcontrast" in loaded_result["tags"]:
            loaded_result2 = loaded_result
        else:
            loaded_result1 = loaded_result

    assert loaded_result1 is not None
    assert loaded_result2 is not None

    test_case = TestCase()
    test_case.maxDiff = None

    test_case.assertDictEqual(result2["tags"], loaded_result2["tags"])
    test_case.assertDictEqual(result2["vals"], loaded_result2["vals"])
    test_case.assertDictEqual(result2["metadata"], loaded_result2["metadata"])
    assert result2["images"].keys() == loaded_result2["images"].keys()
