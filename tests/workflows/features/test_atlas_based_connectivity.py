import os
import pytest

import numpy as np
from nilearn.datasets import fetch_atlas_msdl, fetch_development_fmri
from nilearn.masking import compute_brain_mask

from halfpipe.utils.nipype import run_workflow
from halfpipe.model.feature import Feature
from halfpipe.workflows.features.atlas_based_connectivity import init_atlas_based_connectivity_wf

# TODO harveyaa - WIP CURRENTLY FAILING

# consider scope change
@pytest.fixture(scope="module")
def test_data(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    atlas = fetch_atlas_msdl(data_dir=tmp)
    atlas_filename = atlas["maps"]
    labels = atlas["labels"]
    data = fetch_development_fmri(n_subjects=1, data_dir=tmp)
    mask_img = compute_brain_mask(data.func[0])
    mask_img.to_filename(tmp / 'mask.nii.gz')
    return atlas_filename, labels, data, tmp, tmp / 'mask.nii.gz'

def test_atlas_based_connectivity_wf(test_data: tuple):
    atlas_filename, labels, data, tmp_dir, mask_filename = test_data

    os.chdir(tmp_dir)
    rng = np.random.default_rng(0)

    workdir = tmp_dir / "workdir"
    workdir.mkdir(exist_ok=True)

    # Initialize a wf
    # Features make no sense at all, doing this bypassing them bc I simply cannot understand what they want or what they do
    wf = init_atlas_based_connectivity_wf(workdir,
                                            #optional arguments but don't understand yet
                                        atlas_files = [atlas_filename],
                                        atlas_spaces = ['MNI152NLin2009cAsym'] # update guess of what atlas_spaces wants to something from error trace
                                        # needs either "MNI152NLin6Asym"  "MNI152NLin2009cAsym" (ref: src/halfpipe/interfaces/image_maths/resample.py)
                                            )
    wf.base_dir = workdir
    inputnode = wf.get_node("inputnode")
    assert inputnode is not None

    inputnode.inputs.atlas_names = ['msdl'] # ran up to at least resampling node no fail with this value as non-matching list (?)
    # hangs on resampling node??
    min_region_coverage = 0.8 # default value

    # PASS INPUTS TO INPUTS NODE
    # V1 pass nothing outside constructor for wf
        # ValueError: TSNR requires a value for input 'in_file'. For a list of required inputs, see TSNR.help()
        # 2847.36s
        # SOOOOOO SLOOOOOW
    # V2 pass bold file
        # ValueError: ConnectivityMeasure requires a value for input 'mask_file'. For a list of required inputs, see ConnectivityMeasure.help()
    # V3 pass mask file
        # nipype.pipeline.engine.nodes.NodeExecutionError: Exception raised while executing Node _connectivitymeasure0.
        # (found in error trace) ValueError: Atlas image and data image must have the same shape
            # THIS ERROR SHOULD COME UP EARLIER
            # PUT EVERYTHING IN INPUT NODE & THEN CHECK THE INPUTS

    #  "tags"
    #  "vals"
    #  "metadata",

    #   V2 - inputnode "bold" connected to tsnr "in_file" so should be enough to pass bold to inputnode?
    inputnode.inputs.bold = data['func'][0] # path to .nii.gz file

    #   "mask",
    inputnode.inputs.mask = mask_filename # what exactly is a mask_file? : output from fMRI_prep, path to .nii.gz file w mask

    #   "repetition_time"

    #   "atlas_names", # bypassed these but should've been in constructor inside Feature
    #   "atlas_files", # passed these in constructor
    #   "atlas_spaces", # passed these in constructor
        # resampling to native space
    #   "std2anat_xfm",
    #   "bold_ref_anat",

    run_workflow(wf)
