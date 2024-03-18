# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def compare_fcs(base_fc: Path, current_fc: Path):
    base_matrix = np.loadtxt(base_fc, delimiter="\t")
    current_matrix = np.loadtxt(current_fc, delimiter="\t")
    diff_matrix = np.triu(current_matrix) - np.triu(base_matrix)  # compute difference with one triangle
    mean_abs_diff = np.abs(diff_matrix).mean()

    diff_matrix = (diff_matrix + diff_matrix.T) / 2  # Making it symmetric

    fig, ax = plt.subplots(figsize=(8, 6))
    cax = ax.imshow(diff_matrix, cmap="coolwarm", interpolation="nearest")
    fig.colorbar(cax)
    ax.set_title("Functional Connectivity difference matrix")
    ax.set_xlabel("Regions")
    ax.set_ylabel("Regions")

    return fig, mean_abs_diff


def compare_falff(base_falff: Path, current_fc: Path):
    raise NotImplementedError
