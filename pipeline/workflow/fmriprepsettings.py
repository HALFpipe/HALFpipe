# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from multiprocessing import cpu_count

# Root directory of BIDS dataset
bids_dir = "."

# Treat multiple sessions as longitudinal (may increase runtime)
longitudinal = False

# For multi-echo EPI, use the calculated T2*-map for T2*-driven coregistration
t2s_coreg = False

# Maximum number of threads an individual process may use
omp_nthreads = cpu_count()

# Enable FreeSurfer surface reconstruction (may increase runtime)
freesurfer = False
# Replace medial wall values with NaNs on functional GIFTI files
medial_surface_nan = False
# Enable sub-millimeter preprocessing in FreeSurfer
hires = True

# Name of ANTs skull-stripping template ('OASIS' or 'NKI')
skull_strip_template = "OASIS"

template = "MNI152NLin2009cAsym"
output_spaces = ["template"]

# Preprocessing steps to skip (may include "slicetiming", "fieldmaps")
ignore = []

# Enable debugging outputs
debug = False

# Write uncompressed .nii files in some cases to reduce memory usage
low_mem = False

# Disable functional workflows
anat_only = False

# Enable/disable boundary-based registration refinement.
use_bbr = True
# Degrees-of-freedom for BOLD-T1w registration (6, 9 or 12)
bold2t1w_dof = 9

# Fit B-Spline field using least-squares
fmap_bspline = False
# Demean voxel-shift map during unwarp
fmap_demean = True

# Enable ANTs SyN-based susceptibility distortion correction (SDC).
use_syn = True
# Always run SyN-based SDC even if actual fieldmaps are present
force_syn = False

# Custom reference image for normalization
template_out_grid = op.join(os.getenv("FSLDIR"), 
    "data", "standard", "MNI152_T1_2mm.nii.gz")

# Generate bold CIFTI file in output spaces
cifti_output = False

# Perform ICA-AROMA on MNI-resampled functional series
use_aroma = True

ignore_aroma_err = False

aroma_melodic_dim = None