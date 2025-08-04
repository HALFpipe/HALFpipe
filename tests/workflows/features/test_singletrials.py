import os
import numpy as np
import pandas as pd
import nibabel as nib
from nipype import config
from scipy.stats import gamma
from scipy.signal import fftconvolve
from pathlib import Path
from halfpipe.workflows.features.single_trials import init_singletrials_wf
from types import SimpleNamespace

def build_events_df(onsets, conditions, duration):
    """
    Given onsets array and conditions list,
    returns a pandas DataFrame with onset, duration, trial_type.
    """
    events = []
    for onset, cond in zip(onsets, conditions):
        events.append({
            'onset': float(onset),
            'duration': float(duration),
            'trial_type': cond
        })
    return pd.DataFrame(events)

def spm_hrf(tr, oversampling=16, time_length=32.0, onset=0.0):
    """
    Return values for HRF at temporal resolution tr/oversampling.
    Canonical SPM double-gamma HRF.
    """
    dt = tr / float(oversampling)
    time_vec = np.arange(0, time_length, dt)
    # parameters for the two gamma functions
    peak1 = gamma.pdf(time_vec, 6)      # peak at 6s
    peak2 = gamma.pdf(time_vec, 16) * 0.35  # undershoot
    hrf = peak1 - peak2
    hrf = hrf / np.sum(hrf)  # normalize area=1
    return hrf, oversampling

def convolve_hrf_from_onsets(onsets, hrf, tr, total_time, time_step=0.1):
    """
    Generate an onset vector at high resolution and convolve with HRF.

    Parameters:
    - onsets: list of event onset times (in seconds)
    - hrf: high-resolution HRF (sampled at time_step)
    - tr: repetition time (in seconds)
    - total_time: total duration of scan (in seconds)
    - time_step: high-resolution sampling step (in seconds)

    Returns:
    - convolved signal, downsampled to TR resolution
    """
    n_hr = int(total_time / time_step)
    n_tr = int(total_time / tr)
    highres_vector = np.zeros(n_hr)

    # Fill event onsets
    for onset in onsets:
        idx = int(onset / time_step)
        if idx < len(highres_vector):
            highres_vector[idx] = 1.0

    # Convolve
    full = fftconvolve(highres_vector, hrf)[:n_hr]

    # Downsample to TR resolution
    downsampled = full[::int(tr / time_step)]
    return downsampled[:n_tr]  # clip to match timepoints

def make_half_masks(shape):
    """
    Returns two masks (house_mask, face_mask) splitting along x-axis.
    """
    house = np.zeros(shape, dtype=float)
    house[:shape[0]//2, :, :] = 1.0
    face = np.zeros(shape, dtype=float)
    face[shape[0]//2:, :, :] = 1.0
    return house, face

def generate_4d_data(shape, n_timepoints, events_df, house_mask, face_mask, amp, tr):
    """
    Create 4D data: Gaussian noise + HRF-convolved activations from events_df.
    Returns a 4D numpy array.
    """
    
    # high-resolution HRF
    hrf, _ = spm_hrf(tr=0.1, oversampling=1)
    hrf /= hrf.max()

    total_time = n_timepoints * tr

    # split onsets by condition
    onsets_by_type = {
        "face": events_df.query("trial_type == 'face'")["onset"].tolist(),
        "house": events_df.query("trial_type == 'house'")["onset"].tolist(),
    }

    conv_face  = convolve_hrf_from_onsets(onsets_by_type["face"], hrf, tr, total_time, time_step=0.1) * amp
    conv_house = convolve_hrf_from_onsets(onsets_by_type["house"], hrf, tr, total_time, time_step=0.1) * amp

    # assemble 4D data
    data = np.random.normal(0, 0, size=shape + (n_timepoints,))
    for t in range(n_timepoints):
        data[..., t] += house_mask * conv_house[t]
        data[..., t] += face_mask  * conv_face[t]
    return data

def save_4d_nifti(data_4d, out_path, voxel_size, tr):
    """
    Save a single 4D NIfTI file with given voxel size (mm) and TR (s).
    """
    affine = np.diag([voxel_size, voxel_size, voxel_size, 1.0])
    hdr = nib.Nifti1Header()
    hdr.set_xyzt_units(xyz='mm', t='sec')
    hdr['pixdim'][1:4] = voxel_size
    hdr['pixdim'][4] = tr
    img = nib.Nifti1Image(data_4d, affine, header=hdr)
    nib.save(img, out_path)


def plot_example(data_4d, out_path):

    import matplotlib.pyplot as plt

    # Pick example voxels
    face_voxel  = (8, 5, 5)   # in the "face" half (x >= 5)
    house_voxel = (2, 5, 5)   # in the "house" half (x < 5)

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

def test_singletrials(
    tmp_path: Path,
    shape=(10,10,10),
    n_timepoints=100,
    duration=0,
    amp=5.0,
    tr=2.0
    ):

    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)

    # generate some onsets with jitter
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
        168.05379551502983
    ]

    # set order
    conditions = [
        'house',
        'house',
        'face',
        'face',
        'house',
        'face',
        'face',
        'house',
        'face',
        'face',
        'house',
        'house',
        'face',
        'house'
    ]

    # 1) Build and save events.tsv
    events_df = build_events_df(
        onsets,
        conditions,
        duration
    )

    condition_file = tmp_path / "sub-01_task-HousesFaces_run-1_events.tsv"
    events_df.to_csv(
        condition_file,
        sep='\t',
        index=False
    )

    # create masks
    house_mask, face_mask = make_half_masks(shape)

    # generate 4D data with HRF convolution
    data_4d = generate_4d_data(
        shape,
        n_timepoints,
        events_df,
        house_mask,
        face_mask,
        amp, 
        tr=tr
    )

    plot_example(
        data_4d,
        tmp_path / "example_timecourses.png"
    )

    # 4) Save volumes
    bold_file = tmp_path / "sub-01_ses-1_task-HousesFaces_run-1_bold.nii.gz"
    save_4d_nifti(
        data_4d,
        bold_file,
        voxel_size=2.0,
        tr=tr
    )

    save_4d_nifti(
        house_mask,
        tmp_path / "house.nii.gz",
        voxel_size=2.0,
        tr=1
    )    

    save_4d_nifti(
        face_mask,
        tmp_path / "face.nii.gz",
        voxel_size=2.0,
        tr=1
    )

    # init workflow
    ddict = {
        "name": "SingleTrials",
        "setting": "SingleTrialsSetting",
        "type": "single_trials",
        "conditions": [
            "house",
            "face"
        ],
        "hrf": "dgamma"
    }

    feature = SimpleNamespace(**ddict)
    
    single_trials_wf = init_singletrials_wf(
        condition_files=condition_file,
        condition_units="secs",
        feature=feature,
        workdir=workdir
    )    

    # single_trials_wf.base_dir = workdir  # ensure outputs stay in main workdir
    source_file = bold_file
    inputnode = single_trials_wf.get_node("inputnode").inputs
    inputnode.bold = source_file
    inputnode.mask = tmp_path / "face.nii.gz"
    inputnode.repetition_time = tr
    inputnode.tags = {
        "sub": "01",          # Or whatever subject ID you want
        "ses": "1",
    }

    inputnode.vals = {"scan_start": 0.0}
    graph = single_trials_wf.run()

    (merge_resultdicts,) = [n for n in graph.nodes if n.name == "merge_resultdicts"]

    # assert that face-voxels have higher betas for face
    # order of conditions = specified in ddict (houses, faces)
    # first 7 should have lower betas than second 7

    # LSA
    betas_lsa = nib.load(merge_resultdicts.result.outputs.out[0]["images"]["effect"]).get_fdata()
    n_trials = len(conditions) // 2  # should be 7 if 14 trials
    face_betas_lsa = betas_lsa[face_mask>0, n_trials:]
    house_betas_lsa = betas_lsa[face_mask>0, :n_trials]

    face_sum_lsa = face_betas_lsa.sum()
    house_sum_lsa = house_betas_lsa.sum()
    
    print(f"[LSA]: mask='face'")
    print(f"\ttrial='face'\tbeta={round(face_sum_lsa, 2)}")
    print(f"\ttrial='house'\tbeta={round(house_sum_lsa, 2)}")
    print("")

    assert face_sum_lsa > house_sum_lsa, (
        f"[LSA] Face voxels did not produce higher betas for face trials: "
        f"{face_sum_lsa:.4f} vs {house_sum_lsa:.4f}"
    )

    # LSS
    betas_lss = nib.load(merge_resultdicts.result.outputs.out[1]["images"]["effect"]).get_fdata()
    face_betas_lss = betas_lss[face_mask>0, n_trials:]
    house_betas_lss = betas_lss[face_mask>0, :n_trials]

    face_sum_lss = face_betas_lss.sum()
    house_sum_lss = house_betas_lss.sum()

    print(f"[LSS]: mask='face'")
    print(f"\ttrial='face'\tbeta={round(face_sum_lss, 2)}")
    print(f"\ttrial='house'\tbeta={round(house_sum_lss, 2)}")
    print("")

    assert face_sum_lss > house_sum_lss, (
        f"[LSS] Face voxels did not produce higher betas for face trials: "
        f"{face_sum_lss:.4f} vs {house_sum_lss:.4f}"
    )