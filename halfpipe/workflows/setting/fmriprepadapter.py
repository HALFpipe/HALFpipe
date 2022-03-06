# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import fsl
from niworkflows.interfaces.utility import KeySelect

from ..constants import constants
from ..memory import MemoryCalculator


def init_fmriprep_adapter_wf(
    name: str = "fmriprep_adapter_wf",
    memcalc: MemoryCalculator = MemoryCalculator.default(),
):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_std",
                "bold_mask_std",
                "spatial_reference",
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
    select_std.inputs.key = f"{constants.reference_space}_res-{constants.reference_res}"
    workflow.connect(inputnode, "bold_std", select_std, "bold_std")
    workflow.connect(inputnode, "bold_mask_std", select_std, "bold_mask_std")
    workflow.connect(inputnode, "spatial_reference", select_std, "keys")

    #
    applymask = pe.Node(
        interface=fsl.ApplyMask(),
        name="applymask",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(select_std, "bold_std", applymask, "in_file")
    workflow.connect(select_std, "bold_mask_std", applymask, "mask_file")

    #
    merge = pe.Node(niu.Merge(2), name="merge")
    workflow.connect(applymask, "out_file", merge, "in1")
    workflow.connect(inputnode, "confounds", merge, "in2")

    #
    workflow.connect(merge, "out", outputnode, "files")
    workflow.connect(select_std, "bold_mask_std", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    return workflow
