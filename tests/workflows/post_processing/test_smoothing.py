# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import re
from math import isclose
from pathlib import Path
from shutil import which
from statistics import mean
from subprocess import check_output

import nipype.pipeline.engine as pe
import pytest
from nipype.interfaces import afni

from halfpipe.resource import get as get_resource
from halfpipe.utils.nipype import run_workflow
from halfpipe.workflows.post_processing.smoothing import init_smoothing_wf

from ...resource import setup as setup_test_resources


def volume_smoothness(image_file: Path | str, mask_file: Path | str) -> float:
    wb_command = which("wb_command")
    if wb_command is None:
        raise RuntimeError("wb_command not found")
    output = check_output(
        [wb_command, "-volume-estimate-fwhm", "-roi", str(mask_file), "-whole-file", "-demean", str(image_file)], text=True
    )
    m = re.fullmatch("FWHM: (?P<x>.+), (?P<y>.+), (?P<z>.+)", output.strip())
    if m is None:
        raise RuntimeError(f'Failed to parse wb_command output: "{output}"')
    return mean(map(float, m.groups()))


@pytest.mark.parametrize("target_fwhm", [0, 6])
def test_smoothing_volume(tmp_path, target_fwhm):
    os.chdir(str(tmp_path))

    setup_test_resources()

    in_file = get_resource("sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz")
    brain_file = tmp_path / "brain.nii.gz"
    mask_file = tmp_path / "mask.nii.gz"

    automask = afni.Automask(
        in_file=in_file,
        out_file=mask_file,
        brain_file=brain_file,  # unused
        outputtype="NIFTI_GZ",
    )
    automask.run()

    wf = init_smoothing_wf(target_fwhm)
    wf.base_dir = tmp_path

    inputnode = wf.get_node("inputnode")
    assert isinstance(inputnode, pe.Node)

    inputnode.inputs.files = [str(in_file)]
    inputnode.inputs.mask = str(mask_file)

    graph = run_workflow(wf)

    (merge,) = [n for n in graph.nodes if n.name == "merge"]
    (out_file,) = merge.result.outputs.out

    in_fwhm = volume_smoothness(in_file, mask_file)
    out_fwhm = volume_smoothness(out_file, mask_file)

    if target_fwhm > 0:
        assert target_fwhm <= out_fwhm <= target_fwhm + 1
        assert out_fwhm >= in_fwhm
    else:
        assert isclose(in_fwhm, out_fwhm)


@pytest.mark.skip(reason="not yet implemented")
@pytest.mark.parametrize("target_fwhm", [0, 6])
def test_smoothing_surface(tmp_path, target_fwhm):
    os.chdir(str(tmp_path))

    setup_test_resources()

    in_file = get_resource("sub-50005_task-rest_Atlas_s0.dtseries.nii")

    wf = init_smoothing_wf(target_fwhm)
    wf.base_dir = tmp_path

    inputnode = wf.get_node("inputnode")
    assert isinstance(inputnode, pe.Node)

    inputnode.inputs.files = [str(in_file)]

    graph = run_workflow(wf)

    (merge,) = [n for n in graph.nodes if n.name == "merge"]
    (out_file,) = merge.result.outputs.out

    assert Path(out_file).is_file()
