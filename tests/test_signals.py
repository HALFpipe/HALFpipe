# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os

import nibabel as nib
import numpy as np

from halfpipe.resource import get as get_resource
from halfpipe.signals import mode_signals
from halfpipe.stats.fit import load_data

from .resource import setup as setup_test_resources


def test_fit(tmp_path, wakemandg_hensonrn_raw):
    os.chdir(str(tmp_path))

    cope_files = wakemandg_hensonrn_raw["stat-effect_statmap"]
    var_cope_files = wakemandg_hensonrn_raw["stat-variance_statmap"]
    mask_files = wakemandg_hensonrn_raw["mask"]

    copes_img, var_copes_img = load_data(cope_files, var_cope_files, mask_files)

    setup_test_resources()
    modes_path = get_resource(
        "tpl-MNI152NLin2009cAsym_res-02_atlas-DiFuMo_desc-1024dimensions_probseg.nii.gz"
    )
    modes_img = nib.load(modes_path)

    signals = mode_signals(copes_img, var_copes_img, modes_img)

    assert np.all(np.isfinite(signals))
