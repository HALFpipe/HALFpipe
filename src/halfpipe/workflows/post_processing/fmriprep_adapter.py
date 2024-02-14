# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import fsl
from niworkflows.interfaces.utility import KeySelect

from ...interfaces.utility.remove_volumes import RemoveVolumes
from ..constants import Constants
from ..memory import MemoryCalculator


def init_fmriprep_adapter_wf(
    name: str = "fmriprep_adapter_wf",
    memcalc: MemoryCalculator | None = None,
):
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_std",
                "bold_mask_std",
                "spatial_reference",
                "skip_vols",
                "confounds",
                "vals",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "vals"]),
        name="outputnode",
    )

    select_std = pe.Node(
        KeySelect(fields=["bold_std", "bold_mask_std"]),
        name="select_std",
        run_without_submitting=True,
        nohash=True,
    )
    select_std.inputs.key = f"{Constants.reference_space}_res-{Constants.reference_res}"
    workflow.connect(inputnode, "bold_std", select_std, "bold_std")
    workflow.connect(inputnode, "bold_mask_std", select_std, "bold_mask_std")
    workflow.connect(inputnode, "spatial_reference", select_std, "keys")

    #
    apply_mask = pe.Node(
        interface=fsl.ApplyMask(),
        name="apply_mask",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(select_std, "bold_std", apply_mask, "in_file")
    workflow.connect(select_std, "bold_mask_std", apply_mask, "mask_file")

    #
    merge = pe.Node(niu.Merge(2), name="merge")
    workflow.connect(apply_mask, "out_file", merge, "in1")
    workflow.connect(inputnode, "confounds", merge, "in2")

    #
    skip_vols = pe.MapNode(
        RemoveVolumes(),
        iterfield="in_file",
        name="skip_vols",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(merge, "out", skip_vols, "in_file")
    workflow.connect(inputnode, "skip_vols", skip_vols, "skip_vols")
    workflow.connect(select_std, "bold_mask_std", skip_vols, "mask")

    #
    workflow.connect(skip_vols, "out_file", outputnode, "files")
    workflow.connect(select_std, "bold_mask_std", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    return workflow
