# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Literal

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import fsl

from ...interfaces.utility.remove_volumes import RemoveVolumes
from ..memory import MemoryCalculator


def init_fmriprep_adapter_wf(
    space: Literal["standard", "native"] = "standard",
    name: str | None = None,
    memcalc: MemoryCalculator | None = None,
):
    """
    Following minimal preprocessing in fmriprep, remove data outside of the brain and any dummy scans
    """

    if name is None:
        name = f"fmriprep_adapter_{space}_wf"

    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    workflow = pe.Workflow(name=name)

    match space:
        case "standard":
            bold_file_attr = "bold_file_std"
            bold_mask_attr = "bold_mask_std"
        case "native":
            bold_file_attr = "bold_file_anat"
            bold_mask_attr = "bold_mask_anat"
        case _:
            raise ValueError(f'Unknown space "{space}". Expected "standard" or "native".')

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                bold_file_attr,
                bold_mask_attr,
                # "spatial_reference", # not used anymore
                "dummy_scans",
                "confounds_file",
                "vals",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "vals"]),
        name="outputnode",
    )

    # We apply mask to remove voxels that are outside brain
    apply_mask = pe.Node(
        interface=fsl.ApplyMask(),
        name="apply_mask",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, bold_file_attr, apply_mask, "in_file")
    workflow.connect(inputnode, bold_mask_attr, apply_mask, "mask_file")

    # Take multiple inputs and put them on a list (through Merge node),
    # so we can apply the remove_dummy_scans node to both the bold file and the confounds
    merge = pe.Node(niu.Merge(2), name="merge")
    workflow.connect(apply_mask, "out_file", merge, "in1")
    workflow.connect(inputnode, "confounds_file", merge, "in2")

    # Fmriprep does not actually get rid of volumes we want skipped (in "dummy_scans")
    # so we do it ourselves
    remove_dummy_scans = pe.MapNode(
        RemoveVolumes(),
        iterfield="in_file",
        name="remove_dummy_scans",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(merge, "out", remove_dummy_scans, "in_file")
    workflow.connect(inputnode, "dummy_scans", remove_dummy_scans, "count")
    workflow.connect(inputnode, bold_mask_attr, remove_dummy_scans, "mask")

    workflow.connect(remove_dummy_scans, "out_file", outputnode, "files")
    workflow.connect(inputnode, bold_mask_attr, outputnode, "mask")
    # vals are QC metrics, metadata, scanner metadata
    workflow.connect(inputnode, "vals", outputnode, "vals")

    return workflow
