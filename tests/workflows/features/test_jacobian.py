# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from zipfile import ZipFile

import pytest
from halfpipe.resource import get as get_resource
from halfpipe.utils.nipype import run_workflow
from halfpipe.workflows.features.jacobian import init_jacobian_wf

from ...resource import setup as setup_test_resources


@pytest.fixture(scope="session")
def fmriprep_derivatives(tmp_path_factory) -> Path:
    tmp_path = tmp_path_factory.mktemp("derivatives")

    setup_test_resources()
    zip_path = get_resource("sub-0003_fmriprep_derivatives.zip")

    with ZipFile(zip_path) as zip_file:
        zip_file.extractall(tmp_path)

    return tmp_path


@pytest.fixture(scope="session")
def transform(fmriprep_derivatives: Path) -> Path:
    subject = "sub-0003"
    return fmriprep_derivatives / subject / "anat" / f"{subject}_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5"


def test_jacobian_wf(tmp_path: Path, transform: Path) -> None:
    wf = init_jacobian_wf(transform)
    wf.base_dir = str(tmp_path)
    assert wf.name == "jacobian_wf"

    run_workflow(wf)
