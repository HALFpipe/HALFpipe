# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path

import pytest
from traits.trait_errors import TraitError

from halfpipe.interfaces.connectivity import ConnectivityMeasure


def test_inputs_1():
    """Check that traits validates input type."""
    cm = ConnectivityMeasure()

    with pytest.raises(TraitError):
        cm.inputs.in_file = 2


def test_connectivity_measure(tmp_path: Path) -> None:
    os.chdir(str(tmp_path))

    cm = ConnectivityMeasure()
    cm.inputs.mask_file = "/halfpipe_dev/test_data/conn_test/mask.nii.gz"
    cm.inputs.in_file = "/halfpipe_dev/test_data/conn_test/resampled_func.nii.gz"
    cm.inputs.atlas_file = "/halfpipe_dev/test_data/conn_test/resampled_atlas.nii.gz"

    runtime = cm._run_interface("unsure about this, must be nipype")
