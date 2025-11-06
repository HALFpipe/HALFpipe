import os
import pytest

import numpy as np
from nilearn.datasets import fetch_atlas_msdl, fetch_development_fmri
from nilearn.masking import compute_brain_mask

from halfpipe.utils.nipype import run_workflow
from halfpipe.model.feature import Feature
from halfpipe.workflows.features.atlas_based_connectivity import init_atlas_based_connectivity_wf

# nice when there's internet
#@pytest.fixture(scope="module")
#def test_data(tmp_path_factory):
#    tmp = tmp_path_factory.mktemp("data")
#    atlas = fetch_atlas_msdl(data_dir=tmp)
#    atlas_filename = atlas["maps"]
#    labels = atlas["labels"]
#    data = fetch_development_fmri(n_subjects=1, data_dir=tmp)
#    mask_img = compute_brain_mask(data.func[0])
#    mask_img.to_filename(tmp / 'mask.nii.gz')
#    return atlas_filename, labels, data, tmp, tmp / 'mask.nii.gz'

@pytest.fixture(scope="module")
def tmp_dir(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    return tmp

def test_atlas_based_connectivity_wf(tmp_dir):
    # atlas_filename, labels, data, tmp_dir, mask_filename = test_data
    # bold_filename = data['func'][0]

    # Hard coding paths (within container) - no internet on interactive node 
    mask_filename = '/halfpipe_dev/test_data/conn_test/mask.nii.gz'
    atlas_filename = '/halfpipe_dev/test_data/conn_test/resampled_atlas.nii.gz'
    bold_filename = '/halfpipe_dev/test_data/conn_test/resampled_func.nii.gz'

    os.chdir(tmp_dir)
    rng = np.random.default_rng(0)

    workdir = tmp_dir / "workdir"
    workdir.mkdir(exist_ok=True)

    # Initialize a wf
    # Features make no sense at all, doing this bypassing them bc I simply cannot understand what they want or what they do
    wf = init_atlas_based_connectivity_wf(workdir,
                                            #optional arguments but don't understand yet
                                        atlas_files = [atlas_filename],
                                        atlas_spaces = ['MNI152NLin2009cAsym'], # FOUND IT IN CONSTANTS IT WANTS RESOLUTION 2
                                            )
    wf.base_dir = workdir
    inputnode = wf.get_node("inputnode")
    assert inputnode is not None

    inputnode.inputs.atlas_names = ['msdl'] # ran up to at least resampling node no fail with this value as non-matching list (?)

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
        # ValueError: Atlas image and data image must have the same shape
            # error should come up earlier: put everything in input node & check
            # Lea: resampling of bold is done once in fmri prep pipeline, this assumes that only atlas needs to be resampled - so inputs here must have same shape
            # Hard printed the shapes
                # ATLAS:  (97, 115, 97, 39)
                # VOLUME:  (50, 59, 50) (vs in nilearn (50, 59, 50, 168) what happens to 4th dim?)
            # Cant find input information in the halfpipe debugging outputs
            # but useful to know that inputs were passed 
            # bypassing proper inputs probably broke logging
    # V3 Change to native space (rather than attempt to understand desired spaces etc)
        # whoop that was more confusing
    # V4 I'm passing an atlas and a func file that I resampled already to the same template 
    #   (seems like it should be same as what is in halfpipe MNI152NLin2009cAsym resolution 2 but output dimensions are different e.g. atlas (99, 117, 95, 39) )
    #   passes!
    # V5 found a bug in previous test (was passing the same file as atlas and func yikes) & lea suggested slow test time was due to prob. atlas so changed to destrieux
    # fails!  ValueError: Atlas image and data image must have the same shape
    # very confused, i had thought func data would always be 4d and a non-prob atlas should be 3d 


    #  "tags"
    #  "vals"
    #  "metadata",

    #   V2 - inputnode "bold" connected to tsnr "in_file" so should be enough to pass bold to inputnode?
    inputnode.inputs.bold = bold_filename # path to .nii.gz file

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
