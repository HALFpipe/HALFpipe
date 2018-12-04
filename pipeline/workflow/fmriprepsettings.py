# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

bids_dir = "."
longitudinal = False
t2s_coreg = False
omp_nthreads = 1
freesurfer = False
skull_strip_template = "OASIS"
template = "MNI152NLin2009cAsym"
output_spaces = ["template"]
medial_surface_nan = False
ignore = []
debug = False
low_mem = False
anat_only = False
hires = True
use_bbr = True
bold2t1w_dof = 9
fmap_bspline = False
fmap_demean = True
use_syn = True
force_syn = False
template_out_grid = op.join(os.getenv("FSLDIR"), 
    "data", "standard", "MNI152_T1_2mm.nii.gz")
cifti_output = False
use_aroma = True
ignore_aroma_err = False
aroma_melodic_dim = None