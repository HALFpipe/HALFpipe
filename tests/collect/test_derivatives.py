# -*- coding: utf-8 -*-
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from halfpipe.collect.derivatives import collect_halfpipe_derivatives

paths = [
    "working_directory/derivatives/halfpipe/sub-STRADL/func/task-fearful/sub-STRADL_task-fearful_feature-fearful2_taskcontrast-faceNegVsControl_mask.nii.gz",
    "working_directory/derivatives/halfpipe/sub-STRADL/func/sub-STRADL_task-fearful_stat-tsnr_boldmap.nii.gz",
    "working_directory/derivatives/halfpipe/sub-STRADL/func/task-fearful/sub-STRADL_task-fearful_feature-fearful1_taskcontrast-faceNegVsNeut_stat-sigmasquareds_statmap.nii.gz",
    "working_directory/derivatives/halfpipe/sub-STRADL/func/task-fearful/sub-STRADL_task-fearful_feature-fearful1_taskcontrast-faceNegVsControl_stat-variance_statmap.nii.gz",
    "working_directory/derivatives/halfpipe/sub-STRADL/func/task-fearful/sub-STRADL_task-fearful_feature-fearful3_taskcontrast-faceVsControl_stat-z_statmap.nii.gz",
    "working_directory/derivatives/halfpipe/sub-STRADL/func/task-fearful/sub-STRADL_task-fearful_feature-fearful1_taskcontrast-faceNegVsControl_stat-dof_statmap.nii.gz",
    "working_directory/derivatives/halfpipe/sub-STRADL/func/task-fearful/sub-STRADL_task-fearful_feature-fearful3_taskcontrast-faceVsControl_stat-effect_statmap.nii.gz",
    "working_directory/derivatives/halfpipe/sub-STRADL/func/task-fearful/sub-STRADL_task-fearful_feature-fearful1_desc-contrast_matrix.tsv",
]


def test_collect_halfpipe_derivates(tmp_path: Path) -> None:
    for path_str in paths:
        path = tmp_path / path_str
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.name.endswith(".nii.gz"):
            image = nib.nifti1.Nifti1Image(np.random.rand(10, 10, 10), np.eye(4))
            nib.loadsave.save(image, path)
        else:
            with path.open("wt") as file_handle:
                file_handle.write("1\t2\t3\n")
        if "statmap" in path.name:
            with (path.parent / f"{path.name.removesuffix('.nii.gz')}.json").open("wt") as file_handle:
                json.dump(dict(task_name="fearful", dummy_scans=6), file_handle)
    with (tmp_path / "working_directory/spec.json").open("wt") as file_handle:
        json.dump(dict(), file_handle)
    results = collect_halfpipe_derivatives([tmp_path / "working_directory"])
    for result in results:
        # Ensure that we don't accidentally combine too many images into one result
        assert len(result["images"]) < 3
