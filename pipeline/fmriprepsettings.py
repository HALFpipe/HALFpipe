# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from collections import OrderedDict
from multiprocessing import cpu_count

# Root directory of BIDS dataset
bids_dir = "."

# Perform ICA-AROMA on MNI-resampled functional series
use_aroma = True
err_on_aroma_warn = False
# Maximum number of components identified by MELODIC within ICA-AROMA
aroma_melodic_dim = -200

# Criterion for flagging outliers
regressors_all_comps = False
regressors_dvars_th = 1.5
regressors_fd_th = 0.5

# Treat multiple sessions as longitudinal (may increase runtime)
longitudinal = False

# For multi-echo EPI, use the calculated T2*-map for T2*-driven coregistration
t2s_coreg = False

# Maximum number of threads across all processes
nthreads = cpu_count()

# Maximum number of threads an individual process may use
omp_nthreads = int(nthreads/4)
if nthreads < 4:
    omp_nthreads = int(nthreads/2)

# Enable FreeSurfer surface reconstruction (may increase runtime)
freesurfer = False
# Replace medial wall values with NaNs on functional GIFTI files
medial_surface_nan = False
# Enable sub_millimeter preprocessing in FreeSurfer
hires = True

# Name of ANTs skull-stripping template ('OASIS' or 'NKI')
skull_strip_template = ("OASIS30ANTs", None)

template = {}

# Ordered dictionary where keys are TemplateFlow ID strings
# Values of the dictionary aggregate modifiers
output_spaces = OrderedDict([
    ("MNI152NLin6Asym", {"res": 2}),
    ("MNI152NLin2009cAsym", {"res": 2}),
])
# Option "--use-aroma" requires functional images to be resampled to
# MNI152NLin6Asym space. The argument "MNI152NLin6Asym:res-2" has
# been automatically added to the list of output spaces

# Preprocessing steps to skip (may include "slicetiming", "fieldmaps")
ignore = ["sbref"]

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


settings_dict = {
    "bids_dir": bids_dir,
    "aroma_melodic_dim": aroma_melodic_dim,
    "skull_strip_template": skull_strip_template,
    "longitudinal": longitudinal,
    "freesurfer": freesurfer,
    "hires": hires,
    "ignore": ignore,
    "use_bbr": use_bbr,
    "t2s_coreg": t2s_coreg,
    "bold2t1w_dof": bold2t1w_dof,
    "output_spaces": output_spaces,
    "template": template,
    "medial_surface_nan": medial_surface_nan,
    "cifti_output": cifti_output,
    "omp_nthreads": omp_nthreads,
    "low_mem": low_mem,
    "fmap_bspline": fmap_bspline,
    "fmap_demean": fmap_demean,
    "use_syn": use_syn,
    "force_syn": force_syn,
    "debug": debug,
    "template_out_grid": template_out_grid,
    "use_aroma": use_aroma,
    "aroma_melodic_dim": aroma_melodic_dim,
    "err_on_aroma_warn": err_on_aroma_warn,
    "regressors_all_comps": regressors_all_comps,
    "regressors_dvars_th": regressors_dvars_th,
    "regressors_fd_th": regressors_fd_th
}


class dict_wrapper(object):
    def __init__(self, d):
        self.__dict__ = d


settings = dict_wrapper(settings_dict)
