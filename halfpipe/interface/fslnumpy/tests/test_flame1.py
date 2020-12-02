# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import pytest

import os
import tarfile
from pathlib import Path

import nibabel as nib
import numpy as np

from ....tests.resource import setup as setuptestresources
from ....resource import get as getresource

from ..flame1 import FLAME1
from ...fixes import FLAMEO as FSLFLAMEO

from nipype.interfaces import fsl, ants
from nipype.pipeline import engine as pe
from templateflow.api import get as get_template

from ...imagemaths.merge import _merge, _merge_mask
from ...stats.model import _group_model
from ....utils import first


@pytest.fixture(scope="module")
def wakemandg_hensonrn(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="wakemandg_hensonrn")

    os.chdir(str(tmp_path))

    setuptestresources()
    inputtarpath = getresource("wakemandg_hensonrn_statmaps.tar.gz")

    with tarfile.open(inputtarpath) as fp:
        fp.extractall(tmp_path)

    subjects = [f"{i+1:02d}" for i in range(16)]
    suffixes = ["stat-effect_statmap", "stat-variance_statmap", "mask"]

    data = {
        suffix: [
            tmp_path / f"sub-{subject}_task-faces_feature-taskBased_taskcontrast-facesGtScrambled_model-aggregateTaskBasedAcrossRuns_contrast-intercept_{suffix}.nii.gz"
            for subject in subjects
        ]
        for suffix in suffixes
    }

    data.update({
        "subjects": subjects,
        "spreadsheet": tmp_path / "subjects_age_sex.csv",
    })

    return data


@pytest.fixture(scope="module")
def mni_downsampled(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="mni_downsampled")

    os.chdir(str(tmp_path))

    tpl = get_template("MNI152NLin2009cAsym", resolution=2, desc="brain", suffix="mask")

    result = ants.ResampleImageBySpacing(
        dimension=3,
        input_image=tpl,
        out_spacing=(6, 6, 6)
    ).run()

    return result.outputs.output_image


@pytest.fixture(scope="module")
def wakemandg_hensonrn_downsampled(tmp_path_factory, wakemandg_hensonrn, mni_downsampled):
    tmp_path = tmp_path_factory.mktemp(basename="wakemandg_hensonrn_downsampled")

    os.chdir(str(tmp_path))

    data = dict()

    def _downsample(in_file):
        result = ants.ApplyTransforms(
            dimension=3,
            input_image_type=0,
            input_image=in_file,
            reference_image=mni_downsampled,
            interpolation="NearestNeighbor",
            transforms=["identity"]
        ).run()

        return result.outputs.output_image

    for k, v in wakemandg_hensonrn.items():
        if isinstance(v, list):
            data[k] = [_downsample(f) if Path(f).exists() else f for f in v]
        else:
            data[k] = v

    return data


@pytest.mark.timeout(600)
@pytest.mark.parametrize("use_var_cope", [False, True])
def test_FLAME1(tmp_path, wakemandg_hensonrn_downsampled, use_var_cope):
    os.chdir(str(tmp_path))

    # prepare
    data = wakemandg_hensonrn_downsampled

    cope_files = data["stat-effect_statmap"]
    var_cope_files = data["stat-variance_statmap"]
    mask_files = data["mask"]

    subjects = data["subjects"]
    spreadsheet_file = data["spreadsheet"]

    regressors, contrasts, _ = _group_model(
        subjects=subjects,
        spreadsheet=spreadsheet_file,
        variabledicts=[
            {"name": "Sub", "type": "id"},
            {"name": "Age", "type": "continuous"},
            {"name": "ReactionTime", "type": "categorical"},
        ],
        contrastdicts=[
            {"variable": ["Age"], "type": "infer"},
            {"variable": ["ReactionTime"], "type": "infer"}
        ]
    )

    # run FSL
    merge_cope_file = _merge(cope_files, "t")
    merge_var_cope_file = _merge(var_cope_files, "t")
    merge_mask_file = _merge_mask(mask_files)

    workflow = pe.Workflow("comparison", base_dir=str(tmp_path))

    multipleregressdesign = pe.Node(
        fsl.MultipleRegressDesign(
            regressors=regressors,
            contrasts=contrasts,
        ),
        name="multipleregressdesign",
    )

    flameo = pe.Node(
        FSLFLAMEO(
            run_mode="flame1",
            cope_file=merge_cope_file,
            mask_file=merge_mask_file,
        ),
        name="flameo"
    )

    if use_var_cope:
        flameo.inputs.var_cope_file = merge_var_cope_file

    workflow.connect(multipleregressdesign, "design_mat", flameo, "design_file")
    workflow.connect(multipleregressdesign, "design_con", flameo, "t_con_file")
    workflow.connect(multipleregressdesign, "design_fts", flameo, "f_con_file")
    workflow.connect(multipleregressdesign, "design_grp", flameo, "cov_split_file")

    execgraph = workflow.run()

    # retrieve flameo again
    for node in execgraph.nodes():
        if node.name == "flameo":
            flameo = node

    result = flameo.result

    r0 = dict(
        cope=result.outputs.copes[0],
        tstat=result.outputs.tstats[0],
        fstat=first(result.outputs.fstats),
        tdof=result.outputs.tdof[0],
    )

    # run halfpipe
    instance = FLAME1(
        cope_files=cope_files,
        mask_files=mask_files,
        regressors=regressors,
        contrasts=contrasts,
    )

    if use_var_cope:
        instance.inputs.var_cope_files = var_cope_files

    result = instance.run()

    r1 = dict(
        cope=result.outputs.copes[0],
        tstat=result.outputs.tstats[0],
        fstat=result.outputs.fstats[2],
        tdof=result.outputs.tdof[0],
    )

    # compare
    mask = nib.load(merge_mask_file).get_fdata() > 0

    for k in set(r0.keys()) & set(r1.keys()):
        a0 = nib.load(r0[k]).get_fdata()[mask]
        a1 = nib.load(r1[k]).get_fdata()[mask]

        # weak criteria, determined post-hoc
        # we don't expect exactly identical results, because FSL and numpy
        # use different numerics code and we use double precision while FSL
        # uses single precision floating point
        # so these assertions are here to verify that the small differences
        # will not get any larger with future changes or optimizations

        # no more than one percent of voxels can be more than one percent different
        assert np.isclose(a0, a1, rtol=1e-2).mean() > 0.99, f"Too many diverging voxels for {k}"

        # mean error average needs to be below 0.05
        assert np.abs(a0 - a1).mean() < 0.05, f"Too high mean error average for {k}"
