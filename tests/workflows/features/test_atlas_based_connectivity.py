import os
import pytest

import numpy as np

from templateflow.api import get as get_template
from nilearn.datasets import fetch_development_fmri
from nilearn.masking import compute_brain_mask
from nilearn.image import load_img
from nilearn.image import resample_to_img

#import nibabel as nib
#from nilearn.image import new_img_like

from halfpipe.utils.nipype import run_workflow
from halfpipe.model.feature import Feature
from halfpipe.workflows.features.atlas_based_connectivity import init_atlas_based_connectivity_wf
from halfpipe.resource import get as get_resource

from ...resource import setup as setup_test_resources

# nice when there's internet
@pytest.fixture(scope="module")
def test_data(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")

    # get template
    template_filename = get_template(
                'MNI152NLin2009cAsym',
                resolution=2,
                desc=None,
                suffix="T1w",
            )
    template = load_img(template_filename)
    
    # get func data
    data = fetch_development_fmri(n_subjects=1)
    data_resampled = resample_to_img(data.func[0],template)
    bold_filename = tmp / 'resampled_func.nii.gz'
    data_resampled.to_filename(bold_filename)

    # get mask
    mask_img = compute_brain_mask(bold_filename)
    mask_filename = tmp / "mask.nii.gz"
    mask_img.to_filename(mask_filename)

    # hard coded path within container
    atlas_filename="/halfpipe_dev/test_data/atlases/atlas-DesikanKilliany_dseg.nii.gz"

    #bold_filename = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")
    # online resource
    #setup_test_resources()

    # make mask
    #image_data = nib.nifti1.load(bold_filename).get_fdata()
    #mask_data = image_data.std(axis=3) > 0
    #mask_image = new_img_like(image, data=mask_data, copy_header=True)
    #nib.loadsave.save(mask_image, mask_filename)


    #zooms: tuple[float, ...] = image.header.get_zooms()

    #sampling_period: float = float(zooms[3])  # type: ignore
    #sampling_frequency = 1 / sampling_period

    return atlas_filename, bold_filename, mask_filename, tmp

#@pytest.fixture(scope="module")
#def tmp_dir(tmp_path_factory):
#    tmp = tmp_path_factory.mktemp("data")
#    return tmp

def test_atlas_based_connectivity_wf(test_data):
    atlas_filename, bold_filename, mask_filename, tmp = test_data

    # Hard coding paths (within container) - no internet on interactive node 
    # mask_filename = '/halfpipe_dev/test_data/conn_test/mask.nii.gz'
    # atlas_filename="/halfpipe_dev/test_data/atlases/atlas-DesikanKilliany_dseg.nii.gz"
    # bold_filename = '/halfpipe_dev/test_data/conn_test/resampled_func.nii.gz'

    os.chdir(tmp)
    rng = np.random.default_rng(0)

    workdir = tmp / "workdir"
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

    inputnode.inputs.atlas_names = ['DesikanKilliany_dseg'] # ran up to at least resampling node no fail with this value as non-matching list (?)

    min_region_coverage = 0.8 # default value

    # PASS INPUTS TO INPUTS NODE
    #  "tags"
    #  "vals"
    #  "metadata",

    #   V2 - inputnode "bold" connected to tsnr "in_file" so should be enough to pass bold to inputnode?
    inputnode.inputs.bold = bold_filename # path to .nii.gz file

    #   "mask",
    inputnode.inputs.mask = mask_filename # mask_file output from fMRI_prep, path to .nii.gz file w/ mask

    #   "repetition_time"

    #   "atlas_names", # bypassed these but should've been in constructor inside Feature
    #   "atlas_files", # passed these in constructor
    #   "atlas_spaces", # passed these in constructor
        # resampling to native space
    #   "std2anat_xfm",
    #   "bold_ref_anat",

    graph = run_workflow(wf)

    # Awkward to access node information due to nipype funtion (runs a copy of workflow)
    node_names = [n.names for n in graph.nodes]
    #(out_file,) = merge.result.outputs.out_file

    #image = nib.nifti1.load(out_file)
    #image_data = image.get_fdata()

    #_, after = welch(image_data[mask_data, :].ravel(), sampling_frequency)
    #print node_names
    breakpoint()
