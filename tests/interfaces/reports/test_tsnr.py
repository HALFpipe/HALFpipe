# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nibabel as nib
import numpy as np
from nipype.algorithms import confounds as nac

from halfpipe.interfaces.reports.tsnr import TSNR
from halfpipe.resource import get as get_resource

from ...resource import setup as setup_test_resources


def test_tsnr(tmp_path):
    setup_test_resources()

    data_file = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")

    tsnr = TSNR(in_file=data_file)

    cwd = tmp_path / "tsnr"
    cwd.mkdir()

    result = tsnr.run(cwd=cwd)
    assert result.outputs is not None

    tsnr_image = nib.nifti1.load(result.outputs.out_file)

    reference_tsnr = nac.TSNR(in_file=data_file)

    cwd = tmp_path / "reference_tsnr"
    cwd.mkdir()

    result = reference_tsnr.run(cwd=cwd)
    assert result.outputs is not None

    reference_tsnr_image = nib.nifti1.load(result.outputs.tsnr_file)

    assert np.allclose(tsnr_image.get_fdata(), reference_tsnr_image.get_fdata(), atol=1e-5)
