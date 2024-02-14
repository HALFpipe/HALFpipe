# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from ...interfaces.image_maths.lazy_blur import LazyBlurToFWHM
from ...interfaces.utility.file_type import SplitByFileType
from ..memory import MemoryCalculator


def init_smoothing_wf(
    fwhm: float | None = None,
    memcalc: MemoryCalculator | None = None,
    name: str | None = None,
    suffix: str | None = None,
):
    """
    Smooths a volume within a mask while correcting for the mask edge
    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    if name is None:
        if fwhm is not None:
            name = f"smoothing_{int(float(fwhm) * 1e3):d}_wf"
        else:
            name = "smoothing_wf"
    if suffix is not None:
        name = f"{name}_{suffix}"

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(fields=["files", "mask", "vals", "fwhm"]),
        name="inputnode",
    )
    outputnode = pe.Node(
        interface=niu.IdentityInterface(fields=["files", "mask", "vals"]),
        name="outputnode",
    )

    workflow.connect(inputnode, "mask", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    if fwhm is not None:
        inputnode.inputs.fwhm = float(fwhm)

    split_by_file_type = pe.Node(SplitByFileType(), name="split_by_file_type")
    workflow.connect(inputnode, "files", split_by_file_type, "files")

    smooth = pe.MapNode(
        LazyBlurToFWHM(outputtype="NIFTI_GZ"),
        iterfield="in_file",
        name="smooth",
        mem_gb=memcalc.series_std_gb * 1.5,
    )
    workflow.connect(split_by_file_type, "nifti_files", smooth, "in_file")
    workflow.connect(inputnode, "mask", smooth, "mask")
    workflow.connect(inputnode, "fwhm", smooth, "fwhm")

    merge = pe.Node(niu.Merge(2), name="merge")
    workflow.connect(smooth, "out_file", merge, "in1")
    workflow.connect(split_by_file_type, "tsv_files", merge, "in2")

    workflow.connect(merge, "out", outputnode, "files")

    return workflow
