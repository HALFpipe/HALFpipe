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

    return atlas_filename, bold_filename, mask_filename, tmp


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

    feat = Feature(
        "atlas_based_connectivity", # name
        "atlas_based_connectivity", # type
 
        # kwargs
        **{"atlases":['DesikanKilliany_dseg'],
        "min_region_coverage":0.8,
        }
        )

    # Initialize a wf
    wf = init_atlas_based_connectivity_wf(workdir,
                                        feat,
                                        atlas_files = [atlas_filename],
                                        atlas_spaces = ['MNI152NLin2009cAsym'], # needs resolution 2 (ref: workflows.constants)
                                            )
    wf.base_dir = workdir
    inputnode = wf.get_node("inputnode")
    assert inputnode is not None

    # PASS INPUTS TO INPUTS NODE

    # inputnode "bold" connected to tsnr "in_file"
    inputnode.inputs.bold = bold_filename # path to .nii.gz file
    inputnode.inputs.mask = mask_filename # mask_file output from fMRI_prep, path to .nii.gz file w/ mask
   
    graph = run_workflow(wf)

    # Awkward to access node information due to nipype funtion (runs a copy of workflow)
    node_names = [n.name for n in graph.nodes]
    resultdict_datasink = [n for n in graph.nodes if n.name == 'resultdict_datasink'][0]
    make_resultdicts = [n for n in graph.nodes if n.name == 'make_resultdicts'][0]

    print(resultdict_datasink.inputs)

    print(make_resultdicts.outputs)
 
    assert False
