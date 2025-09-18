import os
from pathlib import Path
from zipfile import ZipFile

import nibabel as nib
from nipype.interfaces import fsl

from halfpipe.interfaces.gift import GicaCmd
from halfpipe.resource import get as get_resource

from ..resource import setup as setup_test_resources


def test_gica_cmd(tmp_path: Path) -> None:
    setup_test_resources()

    data_path = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")

    data_image = nib.nifti1.load(data_path)
    data = data_image.get_fdata()

    os.chdir(str(tmp_path))

    reference = data.mean(axis=-1)
    reference_image = nib.Nifti1Image(reference, data_image.affine, data_image.header)
    nib.save(reference_image, "reference.nii.gz")

    bet = fsl.BET(in_file="reference.nii.gz", mask=True)
    bet.run()

    mask_path = tmp_path / "reference_brain_mask.nii.gz"
    assert mask_path.is_file()

    atlases_path = get_resource("atlases.zip")
    templates = "atlas-NeuroMark_probseg.nii.gz"
    with ZipFile(atlases_path) as zip_file:
        zip_file.extract(templates)

    interface = GicaCmd(data=data_path, mask=mask_path, templates=templates)
    result = interface.run()

    outputs = result.outputs
    assert Path(outputs.components).is_file()
    assert Path(outputs.timecourses).is_file()
    assert Path(outputs.mask).is_file()
    assert Path(outputs.fnc_corrs).is_file()
