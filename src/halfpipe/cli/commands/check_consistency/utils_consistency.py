# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import nilearn.plotting as plotting
import numpy as np
from nilearn import datasets


def reorient_image(input_path, output_path):
    """
    Reorients the NIFTI image to standard orientation using fslreorient2std.
    It will overwrite the original image with the reoriented one.
    """
    try:
        # Overwrite the input file by setting output_path to input_path
        subprocess.run(["fslreorient2std", input_path, output_path], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"An error occurred while reorienting the image: {e}") from e


def highlight_max_changes(ax, diff_matrix, threshold):
    max_change_locations = (
        np.abs(diff_matrix) >= threshold
    )  # Identify locations where the absolute difference exceeds threshold
    # Convert locations to coordinates and plot them on the existing axes
    ax.scatter(*np.where(max_change_locations), color="red", s=1)  # Mark these points in red


def get_network_indices():
    schaefer_atlas = datasets.fetch_atlas_schaefer_2018(n_rois=400, yeo_networks=7, resolution_mm=1)
    labels = [label.decode("utf-8") for label in schaefer_atlas.labels]
    # network_names = [label.split("_")[2] for label in labels]
    network_names_with_hemisphere = ["_".join(label.split("_")[1:3]) for label in labels]

    unique_networks = []
    network_indices = []
    for index, name in enumerate(network_names_with_hemisphere):
        if name not in unique_networks:
            unique_networks.append(name)
            network_indices.append(index)

    return unique_networks, network_indices


def compare_fcs(base_fc: Path, current_fc: Path, threshold):
    # TODO? another interesting thing to compute is whether there are changes of sign.
    base_matrix = np.loadtxt(base_fc, delimiter="\t")
    current_matrix = np.loadtxt(current_fc, delimiter="\t")
    diff_matrix = np.arctanh(current_matrix) - np.arctanh(base_matrix)

    # Calculate metrics
    mean_abs_diff = np.nanmean(np.abs(diff_matrix))  # ignore NaNs in mean
    max_abs_diff = np.nanmax(np.abs(diff_matrix))  # max absolute difference
    nan_base = np.isnan(base_matrix)
    nan_current = np.isnan(current_matrix)
    nan_match = np.mean(nan_base == nan_current) * 100  # Percentage of matching NaN locations

    # Get network indices for plotting
    unique_networks, network_indices = get_network_indices()
    # Extract TestSetting name from the path using regular expression
    match = re.search(r"feature-(TrueComb\d+|FalseComb\d+)", str(base_fc))
    comb_name = match.group(1) if match else "Unknown"

    # Plot
    fig, ax = plt.subplots(figsize=(8, 6))
    cax = ax.imshow(np.tanh(diff_matrix), cmap="coolwarm", interpolation="nearest", vmin=-1, vmax=1)  # cmap = plt.cm.RdBu_r
    fig.colorbar(cax)
    ax.set_title(f"Functional Connectivity difference matrix ({comb_name})")
    ax.set_xlabel("Schaefer atlas regions")
    ax.set_ylabel("Schaefer atlas regions")
    ax.set_xticks(network_indices)
    ax.set_yticks(network_indices)
    ax.set_xticklabels(unique_networks, rotation=90)
    ax.set_yticklabels(unique_networks)

    highlight_max_changes(ax, diff_matrix, threshold)

    annotation = (
        f"Mean Abs Diff: {mean_abs_diff:.4f}\n" f"Max Abs Diff: {max_abs_diff:.4f}\n" f"Matching NaNs: {nan_match:.4f}%"
    )
    ax.text(
        0.5,
        0.98,
        annotation,
        transform=ax.transAxes,
        fontsize=12,
        va="top",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white", alpha=0.8),
    )

    plt.close(fig)  # Close the figure for proper handling in the widget

    return fig, mean_abs_diff, nan_match, max_abs_diff


def histogram_fcs(base_fc: Path, current_fc: Path, default_range=(-1, 1), auto_expand=True):
    base_matrix = np.loadtxt(base_fc, delimiter="\t")
    current_matrix = np.loadtxt(current_fc, delimiter="\t")
    diff_matrix = current_matrix - base_matrix

    # Extract only the upper triangle of the difference matrix, excluding the diagonal
    upper_tri_diff = np.triu(diff_matrix, k=1)  # k=1 starts above the main diagonal
    # Flatten the upper triangle matrix to a 1D array for histogram
    diff_values = upper_tri_diff[upper_tri_diff != 0]  # Exclude zeros, which come from the lower triangle and diagonal

    # Determine the minimum and max values and check if they are out of range
    min_val, max_val = np.min(diff_values), np.max(diff_values)
    range_min, range_max = default_range
    if min_val < range_min or max_val > range_max:
        print(f"Warning: Some values are outside the default range {default_range}.")
        if auto_expand:  # Adjust the range dynamically if auto_expand is True
            range_min = min(min_val, range_min)
            range_max = max(max_val, range_max)
            print(f"Expanded range to include all values: ({range_min}, {range_max})")

    # Create the histogram plot with the updated range
    fig = plt.figure(figsize=(10, 6))
    plt.hist(diff_values, bins=50, color="blue", alpha=0.7, range=(range_min, range_max))
    plt.title("Distribution of Differences in Functional Connectivity")
    plt.xlabel("Difference")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.close()

    return fig


def compare_nii_image(base_img_path: Path, current_img_path: Path):
    # TODO: Infer the type of image based on path name?

    base_img = nib.load(base_img_path)
    current_img = nib.load(current_img_path)
    diff_data = current_img.get_fdata() - base_img.get_fdata()
    mean_abs_diff = np.mean(np.abs(diff_data))  # Calculate MAD
    rmsd = np.sqrt(np.mean(diff_data**2))  # Calculate RMSD
    diff_img = nib.Nifti1Image(diff_data, affine=base_img.affine)
    display = plotting.plot_stat_map(
        diff_img, title="difference in image", display_mode="ortho", cut_coords=(0, 0, 0), cmap="coolwarm"
    )

    return display, mean_abs_diff, rmsd
