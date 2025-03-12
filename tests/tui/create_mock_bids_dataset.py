import json
import os
import random
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd


def create_fake_event_file(num_trials=12, file_name="fake_event_file.tsv", trial_types=None, dry_run=False):
    # Define the possible trial types (if not provided)
    trial_types = [] if trial_types is None else trial_types

    if trial_types:
        # Initialize a list to hold the event data
        events = []

        # Make sure each trial_type appears at least once
        # Shuffle the trial types and add them to events
        for trial_type in trial_types:
            # Randomize the duration between 2 and 3 seconds, rounded to 2 decimals
            duration = round(random.uniform(2, 3), 2)
            # Start with a random onset for each trial_type (random for now)
            current_onset = round(random.uniform(0, 5), 2)
            events.append([current_onset, duration, trial_type])

        # Now generate the remaining events, ensuring that num_trials is filled
        while len(events) < num_trials:
            # Randomize the trial type (either 'cue_negative' or 'img_negative')
            trial_type = random.choice(trial_types)
            # Randomize the duration between 2 and 3 seconds, rounded to 2 decimals
            duration = round(random.uniform(2, 3), 2)
            # Get the last onset and update the current onset
            current_onset = round(events[-1][0] + events[-1][1] + random.uniform(0.5, 1.5), 2)
            events.append([current_onset, duration, trial_type])

        # Shuffle the events list to mix up the order
        random.shuffle(events)

        # Convert the events to a pandas DataFrame for easy output
        df = pd.DataFrame(events, columns=["onset", "duration", "trial_type"])

        # Save the DataFrame to a TSV file
        if not dry_run:
            # Convert file_name to a Path object if it's not already one
            file_name = Path(file_name) if not isinstance(file_name, Path) else file_name
            df.to_csv(file_name, sep="\t", index=False)

        print(f"Fake event file saved as {file_name}")
    else:
        print(f"No event file saved as {file_name}! No conditions for that one!")


def create_mock_anat_nifti_empty(output_path, dry_run=False):
    # Create an empty 3D data array (minimal dimensions, just to satisfy NIfTI structure)
    empty_data = np.zeros((1, 1, 1))

    # Create a NIfTI image with the empty data
    nii_img = nib.Nifti1Image(empty_data, affine=np.eye(4))

    # Save the mock NIfTI file
    if not dry_run:
        nib.save(nii_img, output_path)
    print(f"Mock anat file with header saved to: {output_path}")


def create_mock_func_nifti_with_header(output_path, dry_run=False):
    # Create an empty 3D data array (minimal dimensions, just to satisfy NIfTI structure)
    empty_data = np.zeros((1, 1, 1))

    # Create a NIfTI image with the empty data
    nii_img = nib.Nifti1Image(empty_data, affine=np.eye(4))

    # Manually set the header fields to mock the information you provided
    header = nii_img.header

    header["sizeof_hdr"] = 348
    header["data_type"] = b""
    header["db_name"] = b""
    header["extents"] = 0
    header["session_error"] = 0
    header["regular"] = b"r"
    header["dim_info"] = 0
    header["dim"] = [4, 80, 80, 37, 200, 1, 1, 1]
    header["intent_p1"] = 0.0
    header["intent_p2"] = 0.0
    header["intent_p3"] = 0.0
    header["intent_code"] = 0
    header["datatype"] = 16
    header["bitpix"] = 32
    header["slice_start"] = 0
    header["pixdim"] = [-1.0, 3.0, 3.0, 3.3, 2.0, 0.0, 0.0, 0.0]
    header["vox_offset"] = 0.0
    header["scl_slope"] = np.nan
    header["scl_inter"] = np.nan
    header["slice_end"] = 0
    header["slice_code"] = 0
    header["xyzt_units"] = 10
    header["cal_max"] = 0.0
    header["cal_min"] = 0.0
    header["slice_duration"] = 0.0
    header["toffset"] = 0.0
    header["glmax"] = 0
    header["glmin"] = 0
    header["descrip"] = b"5.0.10"
    header["aux_file"] = b"Piop"
    header["qform_code"] = 1
    header["sform_code"] = 1
    header["quatern_b"] = -0.016865054
    header["quatern_c"] = 0.98754567
    header["quatern_d"] = 0.15574434
    header["qoffset_x"] = 124.18631
    header["qoffset_y"] = -77.02284
    header["qoffset_z"] = -72.6236
    header["srow_x"] = [-2.9970164e00, -1.1356224e-01, -7.7747233e-02, 1.2418631e02]
    header["srow_y"] = [-0.08629788, 2.8527555, -1.0167344, -77.02284]
    header["srow_z"] = [-0.10219894, 0.9213517, 3.1385038, -72.6236]
    header["intent_name"] = b""
    header["magic"] = b"n+1"

    # create json func description file
    desc_data = {
        "EchoTime": 0.02762,
        "RepetitionTime": 0.75,
    }
    # Save the dictionary to a JSON file
    json_file_path = str(output_path).replace(".nii.gz", ".json")

    # Save the mock bold file
    if not dry_run:
        nib.save(nii_img, output_path)
        with open(json_file_path, "w") as json_file:
            json.dump(desc_data, json_file, indent=4)

    print(f"Mock func bold file with header saved to: {output_path}")
    print(f"Mock func json description file save to: {json_file_path}")


def generate_file_names(subject_id=1, tasks=None, type=None):
    type = "bold" if type is None else type
    if type == "bold":
        suffix = "_bold.nii.gz"
    elif type == "event":
        suffix = "_events.tsv"
    else:
        suffix = ""

    # Default tasks if none are provided
    tasks = [] if tasks is None else tasks

    # List to store the generated file names
    updated_file_names = []

    # Loop through tasks
    for task in tasks:
        # Format the file name with the subject and task
        new_file_name = f"sub-{subject_id}_task-{task}{suffix}"
        updated_file_names.append(new_file_name)

    return updated_file_names


def create_bids_data(base_path, number_of_subjects=1, tasks_conditions_dict=None, dry_run=False):
    tasks_conditions_dict = {} if tasks_conditions_dict is None else tasks_conditions_dict

    # Convert the base_path to a Path object
    if not isinstance(base_path, Path):
        base_path = Path(base_path)

    # Loop through the subjects
    for i in range(1, number_of_subjects + 1):
        # Format subject number with leading zeros (e.g., sub-0001)
        subject_id = f"{i:04d}"
        subject_tag = f"sub-{subject_id}"

        # Define paths for 'anat' and 'func' directories
        anat_path = base_path / subject_tag / "anat"
        func_path = base_path / subject_tag / "func"

        print(f"Created: {anat_path}")
        print(f"Created: {func_path}")

        # Create directories (will not crash if they already exist)
        if not dry_run:
            os.makedirs(anat_path, exist_ok=True)
        create_mock_anat_nifti_empty(base_path / subject_tag / "anat" / f"sub-{subject_id}_T1w.nii.gz", dry_run=dry_run)

        os.makedirs(func_path, exist_ok=True)
        for nii_file_name in generate_file_names(subject_id=subject_id, tasks=tasks_conditions_dict.keys(), type="bold"):
            create_mock_func_nifti_with_header(base_path / subject_tag / "func" / nii_file_name, dry_run=dry_run)

        for task, conditions in tasks_conditions_dict.items():
            (event_file_name,) = generate_file_names(subject_id=subject_id, tasks=[task], type="event")
            create_fake_event_file(
                file_name=base_path / subject_tag / "func" / event_file_name, trial_types=conditions, dry_run=dry_run
            )


# # Example usage
# base_path = "ds002785"  # Root directory
# number_of_subjects = 3  # Number of subjects to create directories for
# tasks_conditions_dict = {
#     # 'gstroop_acq-seq':['congruent', 'incongruent'],
#     "anticipation_acq-seq": ["cue_negative", "cue_neutral", "img_negative", "img_neutral"],
#     "workingmemory_acq-seq": ["active_change", "active_nochange", "passive"],
#     "restingstate-mb3": [],
#     # 'emomatching-seq':['control', 'emotion'],
#     # 'faces-mb3':['anger', 'contempt', 'joy', 'neutral', 'pride']
# }
# create_bids_data(base_path, number_of_subjects=number_of_subjects, tasks_conditions_dict=tasks_conditions_dict)
