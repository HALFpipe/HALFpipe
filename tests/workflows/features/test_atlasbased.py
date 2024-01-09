# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pytest
import os
import tarfile
import nibabel as nib
from typing import List
from pathlib import Path
from zipfile import ZipFile
from types import SimpleNamespace

from nilearn.image import new_img_like, resample_to_img

from halfpipe.workflows.features.atlas_based_connectivity import init_atlas_based_connectivity_wf  
from halfpipe.resource import get as get_resource
from halfpipe.utils.nipype import run_workflow
from ...resource import setup as setup_test_resources


@pytest.fixture(scope="module")
def func_file(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="resources")
    os.chdir(str(tmp_path))
    setup_test_resources() #updates resource in halfpipe/resource.py with test resources in tests/resource
    input_path = get_resource("bids_data.zip")
    with ZipFile(input_path) as fp:
        fp.extractall(tmp_path)
    bold_file = tmp_path / "bids_data" / "sub-1012" / "func" / "sub-1012_task-rest_bold.nii.gz"
    bold_img = nib.nifti1.load(bold_file)
    bold_data = bold_img.get_fdata()[..., :64]  # Original func file has 240 timepoints, but we don't need so many volumes for testin
    bold_img = new_img_like(bold_img, bold_data, copy_header=True)
    nib.loadsave.save(bold_img, bold_file)

    return bold_file

@pytest.fixture(scope="module")
def schaefer_atlas(wd: Path, func_file: Path):
    setup_test_resources() 
    atlases_path = get_resource("atlases.zip")
    with ZipFile(atlases_path) as zip_file:
        zip_file.extractall(wd)

    schaefer_path = wd / "atlas-Schaefer2018Combined_dseg.nii.gz"
    atlas_img = nib.nifti1.load(schaefer_path)

    # Resample atlas to match the bold image
    resampled_atlas_img = resample_to_img(source_img=atlas_img, target_img=func_file, interpolation='nearest')
    resampled_atlas_img.to_filename(str(schaefer_path))
    mask_data = (resampled_atlas_img.get_fdata() == 30) 
    mask_img = new_img_like(resampled_atlas_img, mask_data, copy_header=True)

    mask_path = wd / "corrected_mask.nii.gz"
    mask_img.to_filename(str(mask_path))

    return [schaefer_path, mask_path]


@pytest.fixture(scope="session")
def wd(tmp_path_factory) -> Path:
    tmp_path = tmp_path_factory.mktemp("test_fc")
    return tmp_path


def test_atlas_wf_create(wd: Path, func_file, schaefer_atlas: [Path, Path]) -> None:
    # Checks for node existence and configuration
    wf = init_atlas_based_connectivity_wf(
        workdir=str(wd),  
        atlas_files=schaefer_atlas[0], 
        atlas_spaces=["MNI152NLin2009cAsym"]
    )
    wf.base_dir = str(wd)
    assert wf.name == "atlas_based_connectivity_wf"
    assert "inputnode"  in [node.name for node in wf._graph.nodes()]
    assert "make_resultdicts" in [node.name for node in wf._graph.nodes()]
    assert "calcmean" in [node.name for node in wf._graph.nodes()]

def test_atlas_wf_run(wd: Path, func_file, schaefer_atlas: [Path, Path]) -> None:

    wf = init_atlas_based_connectivity_wf(
        workdir=str(wd),  
        atlas_files=schaefer_atlas[0], 
        atlas_spaces=["MNI152NLin2009cAsym"]
    )
    wf.base_dir = str(wd)

    wf.inputs.inputnode.bold = func_file
    wf.inputs.inputnode.mask = schaefer_atlas[1]
    # wf.inputs._calcmean0.in_file = func_file


    print("Validating shapes...")
    print("BOLD image shape:", nib.load(str(func_file)).shape)
    print("Atlas image shape:", nib.load(str(schaefer_atlas[0])).shape)
    # print("Mask image shape:", nib.load(str(schaefer_atlas[1])).shape)
    print(wf.get_node("calcmean").inputs.in_file)


    run_workflow(wf)
