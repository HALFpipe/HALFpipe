# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from collections import OrderedDict

import nibabel as nib
import numpy as np
import pytest
from nipype.interfaces import fsl
from nipype.pipeline import engine as pe

from halfpipe.interfaces.fixes.flameo import FixFLAMEO
from halfpipe.interfaces.image_maths.merge import merge, merge_mask
from halfpipe.logging import logger
from halfpipe.stats.fit import fit

from .base import Dataset


@pytest.mark.slow
@pytest.mark.timeout(1200)
@pytest.mark.parametrize("use_var_cope", [True, False])
def test_flame1(tmp_path, wakemandg_hensonrn: Dataset, use_var_cope):
    os.chdir(str(tmp_path))

    # prepare
    (
        _,
        cope_files,
        var_cope_files,
        mask_files,
        regressors,
        contrasts,
    ) = wakemandg_hensonrn

    # run FSL
    merge_cope_file = merge(cope_files, "t")
    merge_var_cope_file = merge(var_cope_files, "t")
    merge_mask_file = merge_mask(mask_files)

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
        FixFLAMEO(
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

    fsl_result = flameo.result

    fsl_outputs = dict(
        cope=fsl_result.outputs.copes,
        var_cope=fsl_result.outputs.var_copes,
        tstat=fsl_result.outputs.tstats,
        fstat=fsl_result.outputs.fstats,
        zstat=[*fsl_result.outputs.zstats[:2], fsl_result.outputs.zfstats],
        tdof=fsl_result.outputs.tdof,
    )

    # run halfpipe
    if use_var_cope:
        var_cope_files_or_none = var_cope_files
    else:
        var_cope_files_or_none = None

    halfpipe_result = fit(
        cope_files=cope_files,
        var_cope_files=var_cope_files_or_none,
        mask_files=mask_files,
        regressors=regressors,
        contrasts=contrasts,
        algorithms_to_run=["flame1"],
        num_threads=1,
    )
    halfpipe_outputs = dict(
        cope=halfpipe_result["copes"],
        var_cope=halfpipe_result["var_copes"],
        tstat=halfpipe_result["tstats"],
        fstat=halfpipe_result["fstats"],
        zstat=halfpipe_result["zstats"],
        tdof=halfpipe_result["dof"],
    )

    # Compare
    mask = nib.nifti1.load(merge_mask_file).get_fdata() > 0
    comparison_keys = set(fsl_outputs.keys()) & set(halfpipe_outputs.keys())
    for key in comparison_keys:
        fsl_paths = fsl_outputs[key]
        if isinstance(fsl_paths, str):
            fsl_paths = [fsl_paths]
        fsl_images = [nib.nifti1.load(fsl_path) for fsl_path in fsl_paths]

        halfpipe_paths = halfpipe_outputs[key]
        halfpipe_images: list[nib.analyze.AnalyzeImage] = list()
        for halfpipe_path in halfpipe_paths:
            if not halfpipe_path:
                continue
            image = nib.nifti1.load(halfpipe_path)
            image = nib.funcs.squeeze_image(image)
            if image.ndim == 4:
                volumes = nib.funcs.four_to_three(image)
                if key == "tdof":
                    # Skip numerator degrees of freedom
                    halfpipe_images.append(volumes[1])
                else:
                    halfpipe_images.extend(volumes)
            else:
                halfpipe_images.append(image)

        for fsl_image, halfpipe_image in zip(fsl_images, halfpipe_images, strict=False):
            a0 = fsl_image.get_fdata()[mask]
            a1 = halfpipe_image.get_fdata()[mask]

            # Weak criteria, determined post-hoc
            # We don't expect exactly identical results, because FSL and numpy
            # use different numerics code and we use double precision while FSL
            # uses single precision floating point
            # so these assertions are here to verify that the small differences
            # will not get any larger with future changes or optimizations

            if a0.var() > 0:
                correlation = np.corrcoef(a0, a1)[0, 1].item()
                logger.info(f"Correlation for {key}: {correlation}")
                assert correlation > 0.999, f"Correlation too low for {key}"

            diverging_voxels = np.logical_not(np.isclose(a0, a1, rtol=1e-2))
            if diverging_voxels.any():
                diverging_voxel_proportion = diverging_voxels.mean().item()
                logger.info(f"Diverging voxel proportion for {key}: {diverging_voxel_proportion}")
                assert diverging_voxel_proportion < 0.05, f"Too many diverging voxels for {key}"
            else:
                logger.info(f"No diverging voxels for {key}")

            if key in frozenset(["var_cope"]):  # Skip these for varcope
                continue

            if diverging_voxels.any():
                difference_in_diverging_voxels = np.abs(a0 - a1)[diverging_voxels]
                logger.info(f"Max difference in diverging voxels for {key}: {difference_in_diverging_voxels.max()}")
                assert np.all(difference_in_diverging_voxels < 50), f"Difference in diverging voxels is too big for {key}"

            # Mean error needs to be below 0.05
            mean_error = np.abs(a0 - a1).mean()
            logger.info(f"Mean error average for {key}: {mean_error}")
            assert float(mean_error) < 5e-2, f"Too high mean error average for {key}"
