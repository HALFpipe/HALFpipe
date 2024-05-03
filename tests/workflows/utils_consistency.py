# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


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


def compare_fcs(base_fc: Path, current_fc: Path):
    base_matrix = np.loadtxt(base_fc, delimiter="\t")
    current_matrix = np.loadtxt(current_fc, delimiter="\t")
    diff_matrix = np.triu(current_matrix) - np.triu(base_matrix)  # compute difference with one triangle

    #! Correct this because it won't be able to handle the NaNs
    mean_abs_diff = np.abs(diff_matrix).mean()

    diff_matrix = (diff_matrix + diff_matrix.T) / 2  # Making it symmetric

    fig, ax = plt.subplots(figsize=(8, 6))
    cax = ax.imshow(diff_matrix, cmap="coolwarm", interpolation="nearest")
    fig.colorbar(cax)
    ax.set_title("Functional Connectivity difference matrix")
    ax.set_xlabel("Atlas regions")
    ax.set_ylabel("Atlas regions")

    return fig, mean_abs_diff


def compare_falff(base_falff: Path, current_fc: Path):
    raise NotImplementedError
