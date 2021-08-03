# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import pytest

import os
from collections import OrderedDict

import nibabel as nib
import numpy as np

from ..fit import fit
from ...interface.fixes import FLAMEO as FSLFLAMEO

from nipype.interfaces import fsl
from nipype.pipeline import engine as pe

from ...interface.imagemaths.merge import _merge, _merge_mask
from ..design import group_design


@pytest.mark.slow
@pytest.mark.timeout(600)
@pytest.mark.parametrize("use_var_cope", [True, False])
def test_FLAME1(tmp_path, wakemandg_hensonrn_downsampled, use_var_cope):
    os.chdir(str(tmp_path))

    # prepare
    data = wakemandg_hensonrn_downsampled

    cope_files = data["stat-effect_statmap"]
    var_cope_files = data["stat-variance_statmap"]
    mask_files = data["mask"]

    subjects = data["subjects"]
    spreadsheet_file = data["spreadsheet"]

    regressors, contrasts, _, _ = group_design(
        subjects=subjects,
        spreadsheet=spreadsheet_file,
        variabledicts=[
            {"name": "Sub", "type": "id"},
            {"name": "Age", "type": "continuous"},
            {"name": "ReactionTime", "type": "categorical"},
        ],
        contrastdicts=[
            {"variable": ["Age"], "type": "infer"},
            {"variable": ["ReactionTime"], "type": "infer"},
        ],
    )

    # run FSL
    merge_cope_file = _merge(cope_files, "t")
    merge_var_cope_file = _merge(var_cope_files, "t")
    merge_mask_file = _merge_mask(mask_files)

    workflow = pe.Workflow("comparison", base_dir=str(tmp_path))

    demeaned_regressors = OrderedDict()  # need to manually demean here
    for variable_name, values in regressors.items():
        if variable_name.lower() != "intercept":
            values = (np.array(values) - np.nanmean(values)).tolist()
        demeaned_regressors[variable_name] = values

    multipleregressdesign = pe.Node(
        fsl.MultipleRegressDesign(
            regressors=demeaned_regressors,
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
        name="flameo",
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
        var_cope=result.outputs.var_copes[0],
        tstat=result.outputs.tstats[0],
        fstat=result.outputs.fstats,
        tdof=result.outputs.tdof[0],
    )

    # run halfpipe
    if use_var_cope:
        var_cope_files_or_none = var_cope_files
    else:
        var_cope_files_or_none = None

    result = fit(
        cope_files=cope_files,
        var_cope_files=var_cope_files_or_none,
        mask_files=mask_files,
        regressors=regressors,
        contrasts=contrasts,
        algorithms_to_run=["flame1"],
        num_threads=1,
    )

    r1 = dict(
        cope=result["copes"][0],
        var_cope=result["var_copes"][0],
        tstat=result["tstats"][0],
        fstat=result["fstats"][2],
        tdof=result["dof"][0],
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

        # max difference of one percent
        assert (
            float(np.isclose(a0, a1, rtol=1e-2).mean()) > 0.995
        ), f"Too many diverging voxels for {k}"

        if k not in frozenset(["var_cope"]):
            assert np.all(
                np.abs(a0 - a1)[
                    np.logical_not(np.isclose(a0, a1, rtol=1e-2))
                ] < 25
            ), f"Difference in diverging voxels is too big for {k}"

            # mean error average needs to be below 0.05
            assert float(np.abs(a0 - a1).mean()) < 5e-2, f"Too high mean error average for {k}"
