from pathlib import Path

import nibabel as nib
import numpy as np
from nipype.interfaces.ants import ApplyTransforms
from templateflow.api import get as get_template

from halfpipe.interfaces.reports.vals import CalcMean
from halfpipe.resource import get as get_resource

from ...resource import setup as setup_test_resources


def test_calc_mean_matrix(tmp_path: Path, atlases_maps_seed_images_path: Path) -> None:
    setup_test_resources()

    in_file = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")
    parcellation = atlases_maps_seed_images_path / "atlas-DesikanKilliany_dseg.nii.gz"

    apply_transforms = ApplyTransforms(
        interpolation="NearestNeighbor",
        input_image=in_file,
        reference_image=parcellation,
        transforms="identity",
        input_image_type=3,  # Time series
    )
    cwd = tmp_path / "apply_transforms"
    cwd.mkdir()
    result = apply_transforms.run(cwd=cwd)
    in_file = result.outputs.output_image

    calc_mean_interface = CalcMean(in_file=in_file, parcellation=parcellation)

    cwd = tmp_path / "calc_mean"
    cwd.mkdir()

    result = calc_mean_interface.run(cwd=cwd)
    assert result.outputs is not None

    _, _, _, target_volume_count = nib.nifti1.load(in_file).shape
    volume_count, region_count = result.outputs.mean_matrix.shape
    assert volume_count == target_volume_count
    assert region_count == 68


def test_calc_means(tmp_path: Path, atlases_maps_seed_images_path: Path) -> None:
    parcellation = atlases_maps_seed_images_path / "atlas-DesikanKilliany_dseg.nii.gz"

    calc_mean_interface = CalcMean(in_file=parcellation, parcellation=parcellation)

    cwd = tmp_path / "calc_mean"
    cwd.mkdir()

    result = calc_mean_interface.run(cwd=cwd)
    assert result.outputs is not None
    assert len(result.outputs.means) == 68
    assert result.outputs.means == list(map(float, range(1, 69)))


def test_calc_mean(tmp_path: Path, atlases_maps_seed_images_path: Path) -> None:
    parcellation = atlases_maps_seed_images_path / "atlas-DesikanKilliany_dseg.nii.gz"
    mask = get_template("MNI152NLin2009cAsym", resolution=2, desc="brain", suffix="mask")

    calc_mean_interface = CalcMean(in_file=parcellation, mask=mask)

    cwd = tmp_path / "calc_mean"
    cwd.mkdir()

    result = calc_mean_interface.run(cwd=cwd)
    assert result.outputs is not None
    assert isinstance(result.outputs.mean, float)
    assert np.isfinite(result.outputs.mean)
