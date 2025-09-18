from pathlib import Path
from typing import Any, Literal

import nibabel as nib
import numpy as np
import pandas as pd
import pytest
from numpy import typing as npt
from scipy.signal import fftconvolve
from scipy.stats import gamma

from halfpipe.logging import logger
from halfpipe.model.feature import FeatureSchema
from halfpipe.workflows.features.task_based import init_task_based_wf

shape: tuple[int, int, int] = (10, 10, 10)
n_timepoints: int = 100
amplitude: float = 5.0
repetition_time: float = 2.0
voxel_size: float = 2.0


def spm_hrf(repetition_time: float, oversampling: float, time_length: float = 32.0) -> npt.NDArray[np.float64]:
    """
    Return values for HRF at temporal resolution repetition_time/oversampling.
    Canonical SPM double-gamma HRF.
    """
    dt = repetition_time / float(oversampling)
    time_vec = np.arange(0, time_length, dt)
    # parameters for the two gamma functions
    peak1 = gamma.pdf(time_vec, 6)  # peak at 6s
    peak2 = gamma.pdf(time_vec, 16) * 0.35  # undershoot
    hrf = peak1 - peak2
    hrf = hrf / np.sum(hrf)  # normalize area=1
    return hrf


def convolve_hrf_from_onsets(
    onsets: list[float], hrf: npt.NDArray[np.float64], total_time: float, time_step: float = 0.1
) -> npt.NDArray[np.float64]:
    """
    Generate an onset vector at high resolution and convolve with HRF.

    Parameters:
    - onsets: list of event onset times (in seconds)
    - hrf: high-resolution HRF (sampled at time_step)
    - total_time: total duration of scan (in seconds)
    - time_step: high-resolution sampling step (in seconds)

    Returns:
    - convolved signal, downsampled to TR resolution
    """
    n_hr = int(total_time / time_step)
    n_tr = int(total_time / repetition_time)
    highres_vector = np.zeros(n_hr)

    # Fill event onsets
    for onset in onsets:
        idx = int(onset / time_step)
        if idx < len(highres_vector):
            highres_vector[idx] = 1.0

    # Convolve
    full = fftconvolve(highres_vector, hrf)[:n_hr]

    # Downsample to TR resolution
    downsampled = full[:: int(repetition_time / time_step)]
    return downsampled[:n_tr]  # clip to match timepoints


def save_4d_nifti(data_4d: npt.NDArray[np.float64], out_path: Path) -> None:
    """
    Save a single 4D NIfTI file with given voxel size (mm) and TR (s).
    """
    affine = np.diag([voxel_size, voxel_size, voxel_size, 1.0])
    hdr = nib.Nifti1Header()
    hdr.set_xyzt_units(xyz="mm", t="sec")
    hdr["pixdim"][1:4] = voxel_size
    hdr["pixdim"][4] = repetition_time
    img = nib.Nifti1Image(data_4d, affine, header=hdr)
    nib.save(img, out_path)


def plot_example(data_4d: npt.NDArray[np.float64], out_path: Path) -> None:
    import matplotlib.pyplot as plt

    # Pick example voxels
    face_voxel = (8, 5, 5)  # in the "face" half (x >= 5)
    house_voxel = (2, 5, 5)  # in the "house" half (x < 5)

    # Extract timecourses
    tc_face = data_4d[face_voxel]
    tc_house = data_4d[house_voxel]

    # Plot
    fig, axs = plt.subplots(figsize=(10, 5), constrained_layout=True)
    axs.plot(tc_face, label="Face voxel", lw=2)
    axs.plot(tc_house, label="House voxel", lw=2)
    axs.set_xlabel("Time (TRs)")
    axs.set_ylabel("Signal intensity")
    axs.set_title("Example voxel timecourses")
    axs.legend()

    fig.savefig(out_path)
    plt.close(fig)


@pytest.fixture(scope="session")
def half_masks() -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """
    Returns two masks (house_mask, face_mask) splitting along x-axis.
    """
    house = np.zeros(shape, dtype=float)
    house[: shape[0] // 2, :, :] = 1.0
    face = np.zeros(shape, dtype=float)
    face[shape[0] // 2 :, :, :] = 1.0
    return house, face


# Some onsets with jitter
onsets = [
    10.257801082299062,
    28.048984370225746,
    43.323283486204126,
    56.34091764205242,
    69.47620661836409,
    77.49889380935444,
    86.13188781960628,
    96.8891562508195,
    106.3304476228412,
    114.43813702339415,
    131.24871513882664,
    146.2612368172774,
    156.64656043381945,
    168.05379551502983,
]

duration = 0.0

# set order
conditions = [
    "house",
    "house",
    "face",
    "face",
    "house",
    "face",
    "face",
    "house",
    "face",
    "face",
    "house",
    "house",
    "face",
    "house",
]


@pytest.fixture(scope="session")
def events_df() -> pd.DataFrame:
    """
    Given onsets array and conditions list,
    returns a pandas DataFrame with onset, duration, trial_type.
    """

    events = []
    for onset, cond in zip(onsets, conditions, strict=False):
        events.append({"onset": float(onset), "duration": float(duration), "trial_type": cond})
    return pd.DataFrame(events)


@pytest.fixture(scope="session")
def condition_file(tmp_path_factory, events_df: pd.DataFrame) -> Path:
    tmp_path = tmp_path_factory.mktemp(basename="simulated_events")
    condition_file = tmp_path / "sub-01_task-HousesFaces_run-1_events.tsv"
    events_df.to_csv(condition_file, sep="\t", index=False)
    return condition_file


@pytest.fixture(scope="session")
def simulated_bold_file(
    tmp_path_factory, half_masks: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]], events_df: pd.DataFrame
) -> Path:
    """
    Create 4D data: Gaussian noise + HRF-convolved activations from events_df.
    Returns path to a NIfTI file.
    """

    tmp_path = tmp_path_factory.mktemp(basename="simulated_bold")

    # Generate 4D data with HRF convolution
    house_mask, face_mask = half_masks

    # high-resolution HRF
    time_step = 0.1
    hrf = spm_hrf(repetition_time=time_step, oversampling=1)
    hrf /= hrf.max()

    total_time = n_timepoints * repetition_time

    # split onsets by condition
    onsets_by_type = {
        "face": events_df.query("trial_type == 'face'")["onset"].tolist(),
        "house": events_df.query("trial_type == 'house'")["onset"].tolist(),
    }

    conv_face = convolve_hrf_from_onsets(onsets_by_type["face"], hrf, total_time, time_step=time_step) * amplitude
    conv_house = convolve_hrf_from_onsets(onsets_by_type["house"], hrf, total_time, time_step=time_step) * amplitude

    # Assemble 4D data
    data = np.random.normal(0, 0, size=shape + (n_timepoints,))
    for t in range(n_timepoints):
        data[..., t] += house_mask * conv_house[t]
        data[..., t] += face_mask * conv_face[t]

    plot_example(data, tmp_path / "example_timecourses.png")

    # Save volumes
    bold_file = tmp_path / "sub-01_ses-1_task-HousesFaces_run-1_bold.nii.gz"
    save_4d_nifti(data, bold_file)
    save_4d_nifti(house_mask, tmp_path / "house.nii.gz")
    save_4d_nifti(face_mask, tmp_path / "face.nii.gz")

    return bold_file


@pytest.mark.parametrize(
    "estimation", ["multiple_trial", "single_trial_least_squares_single", "single_trial_least_squares_all"]
)
def test_task_based(
    tmp_path: Path,
    estimation: Literal["multiple_trial", "single_trial_least_squares_single", "single_trial_least_squares_all"],
    simulated_bold_file: Path,
    condition_file: Path,
    half_masks: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)

    # Create workflow
    ddict: dict[str, Any] = {
        "name": "TaskBased",
        "setting": "TaskBasedSetting",
        "type": "task_based",
        "estimation": estimation,
        "conditions": ["house", "face"],
        "hrf": "dgamma",
    }
    if estimation == "multiple_trial":
        ddict["contrasts"] = [
            dict(type="t", name="faceGtHouse", variable=["face", "house"], values={"face": 1.0, "house": -1.0}),
        ]

    feature_schema = FeatureSchema()
    feature = feature_schema.load(ddict)

    wf = init_task_based_wf(condition_files=(str(condition_file),), condition_units="secs", feature=feature, workdir=workdir)

    source_file = simulated_bold_file
    inputnode = wf.get_node("inputnode")
    inputnode.inputs.bold = source_file
    inputnode.inputs.repetition_time = repetition_time
    inputnode.inputs.tags = {
        "sub": "01",  # Or whatever subject ID you want
        "ses": "1",
    }

    inputnode.inputs.vals = {"scan_start": 0.0}
    graph = wf.run()

    (make_resultdicts,) = [n for n in graph.nodes if n.name == "make_resultdicts"]
    resultdicts = make_resultdicts.result.outputs.resultdicts

    # Test that face-voxels have higher betas for face
    # order of conditions = specified in ddict (houses, faces)
    # first 7 should have lower betas than second 7

    house_mask, face_mask = half_masks

    if estimation == "multiple_trial":
        (resultdict,) = resultdicts
        betas = nib.nifti1.load(resultdict["images"]["effect"]).get_fdata()

        face_betas = betas[face_mask > 0]
        house_betas = betas[house_mask > 0]
    else:  # Single trial estimation
        (face_file,) = (
            resultdict["images"]["effect"] for resultdict in resultdicts if resultdict["tags"]["condition"] == "face"
        )
        (house_file,) = (
            resultdict["images"]["effect"] for resultdict in resultdicts if resultdict["tags"]["condition"] == "house"
        )

        face_betas = nib.nifti1.load(face_file).get_fdata()
        house_betas = nib.nifti1.load(house_file).get_fdata()

        face_betas = face_betas[face_mask > 0]
        house_betas = house_betas[face_mask > 0]

        n_trials = len(conditions) // 2  # should be 7 if 14 trials
        assert face_betas.shape[-1] == n_trials, "Face betas do not have the expected number of trials"
        assert house_betas.shape[-1] == n_trials, "House betas do not have the expected number of trials"

    logger.info(f'trial="face"\tbeta={face_betas.mean():.4f}')
    logger.info(f'trial="house"\tbeta={house_betas.mean():.4f}')

    assert face_betas.mean() > house_betas.mean(), (
        f"Face voxels did not produce higher betas for face trials: {face_betas.mean():.4f} vs {house_betas.mean():.4f}"
    )
