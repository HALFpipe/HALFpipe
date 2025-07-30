# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Literal

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import afni

from ...interfaces.image_maths.lazy_blur import LazyBlurToFWHM
from ...interfaces.image_maths.zscore import ZScore
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.make import MakeResultdicts
from ...model.feature import Feature
from ...utils.format import format_workflow
from ..memory import MemoryCalculator


def compute_falff(mask_file: str, filtered_file: str, unfiltered_file: str) -> tuple[str, str]:
    """
    Computes fALFF using Nibabel instead of AFNI's 3dcalc.
    """

    from functools import reduce
    from pathlib import Path

    import nibabel as nib
    import numpy as np
    from nilearn.image import new_img_like

    mask_image = nib.nifti1.load(mask_file)
    filtered_image = nib.nifti1.load(filtered_file)
    unfiltered_image = nib.nifti1.load(unfiltered_file)

    filtered = filtered_image.get_fdata()
    unfiltered = unfiltered_image.get_fdata()

    mask = reduce(
        np.logical_and,
        [
            np.asanyarray(mask_image.dataobj, dtype=np.bool_),
            np.isfinite(filtered),
            np.isfinite(unfiltered),
            np.logical_not(np.isclose(unfiltered, 0.0)),
        ],
    )

    mask_image = new_img_like(mask_image, mask, copy_header=True)
    mask_file = str(Path("mask.nii.gz").resolve())
    nib.loadsave.save(mask_image, mask_file)

    falff = np.zeros_like(filtered)
    falff[mask] = filtered[mask] / unfiltered[mask]

    falff_image = nib.nifti1.Nifti1Image(falff, affine=filtered_image.affine, header=filtered_image.header)
    falff_file = str(Path("falff.nii.gz").resolve())
    nib.loadsave.save(falff_image, falff_file)

    return mask_file, falff_file


def init_falff_wf(
    workdir: str | Path,
    feature: Feature | None = None,
    fwhm: float | None=None,
    space: Literal["standard", "native"] = "standard",
    memcalc: MemoryCalculator | None = None,
) -> pe.Workflow:
    """
    Calculate Amplitude of low frequency oscillations(ALFF) and
    fractional ALFF maps

    Returns
    -------
    workflow : workflow object
        ALFF workflow

    Notes
    -----
    Adapted from
    <https://github.com/FCP-INDI/C-PAC/blob/master/CPAC/alff/alff.py>

    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    if feature is not None:
        name = f"{format_workflow(feature.name)}"
    else:
        name = "falff"
    if fwhm is not None:
        name = f"{name}_{int(float(fwhm) * 1e3):d}"
    name = f"{name}_wf"
    workflow = pe.Workflow(name=name)

    # input and output nodes
    inputnode = pe.Node(
        niu.IdentityInterface(fields=["tags", "vals", "metadata", "bold", "mask", "fwhm"]),
        name="inputnode",
    )
    unfiltered_inputnode = pe.Node(
        niu.IdentityInterface(fields=["bold", "mask"]),
        name="unfiltered_inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    if fwhm is not None:
        inputnode.inputs.fwhm = float(fwhm)
    elif feature is not None and hasattr(feature, "smoothing"):
        inputnode.inputs.fwhm = feature.smoothing.get("fwhm")

    # setup results
    make_resultdicts = pe.Node(
        MakeResultdicts(tagkeys=["feature"], imagekeys=["alff", "falff", "mask"]),
        name="make_resultdicts",
    )
    if feature is not None:
        make_resultdicts.inputs.feature = feature.name
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
    workflow.connect(inputnode, "mask", make_resultdicts, "mask")

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    # setup datasink
    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=workdir), name="resultdict_datasink")
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    # standard deviation of the filtered image is the alff
    stddev_filtered = pe.Node(afni.TStat(), name="stddev_filtered", mem_gb=memcalc.series_std_gb)
    stddev_filtered.inputs.outputtype = "NIFTI_GZ"
    stddev_filtered.inputs.options = "-stdev"
    workflow.connect(inputnode, "bold", stddev_filtered, "in_file")
    workflow.connect(inputnode, "mask", stddev_filtered, "mask")

    # smooth and scale alff
    smooth = pe.MapNode(LazyBlurToFWHM(outputtype="NIFTI_GZ"), iterfield="in_file", name="smooth_alff")
    workflow.connect(stddev_filtered, "out_file", smooth, "in_file")
    workflow.connect(inputnode, "mask", smooth, "mask")
    workflow.connect(inputnode, "fwhm", smooth, "fwhm")

    zscore = pe.MapNode(ZScore(), iterfield="in_file", name="zscore_alff", mem_gb=memcalc.volume_std_gb)
    workflow.connect(smooth, "out_file", zscore, "in_file")
    workflow.connect(inputnode, "mask", zscore, "mask")
    workflow.connect(zscore, "out_file", make_resultdicts, "alff")

    # standard deviation of the unfiltered image
    stddev_unfiltered = pe.Node(afni.TStat(), name="stddev_unfiltered", mem_gb=memcalc.series_std_gb)
    stddev_unfiltered.inputs.outputtype = "NIFTI_GZ"
    stddev_unfiltered.inputs.options = "-stdev"
    workflow.connect(unfiltered_inputnode, "bold", stddev_unfiltered, "in_file")
    workflow.connect(unfiltered_inputnode, "mask", stddev_unfiltered, "mask")

    # calculate falff
    falff = pe.Node(
        niu.Function(
            input_names=["mask_file", "filtered_file", "unfiltered_file"],
            output_names=["mask_file", "falff_file"],  # type: ignore
            function=compute_falff,
        ),
        name="falff",
    )

    workflow.connect(inputnode, "mask", falff, "mask_file")
    workflow.connect(stddev_filtered, "out_file", falff, "filtered_file")
    workflow.connect(stddev_unfiltered, "out_file", falff, "unfiltered_file")

    # smooth and scale falff
    smooth = pe.MapNode(LazyBlurToFWHM(outputtype="NIFTI_GZ"), iterfield="in_file", name="smooth_falff")
    workflow.connect(falff, "falff_file", smooth, "in_file")
    workflow.connect(inputnode, "mask", smooth, "mask")
    workflow.connect(inputnode, "fwhm", smooth, "fwhm")

    zscore = pe.MapNode(ZScore(), iterfield="in_file", name="zscore_falff", mem_gb=memcalc.volume_std_gb)
    workflow.connect(smooth, "out_file", zscore, "in_file")
    workflow.connect(inputnode, "mask", zscore, "mask")
    workflow.connect(zscore, "out_file", make_resultdicts, "falff")

    return workflow
