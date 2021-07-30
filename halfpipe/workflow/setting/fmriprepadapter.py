# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl

from ...interface import Exec
from ..memory import MemoryCalculator


def init_fmriprep_adapter_wf(name="fmriprep_adapter_wf", memcalc=MemoryCalculator.default()):
    """
    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        Exec(
            fieldtpls=[
                ("bold_std", "firststr"),
                ("bold_mask_std", "firststr"),
                ("confounds", "firststr"),
                ("vals", None)
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "vals"]),
        name="outputnode",
    )

    #
    applymask = pe.Node(
        interface=fsl.ApplyMask(),
        name="applymask",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "bold_std", applymask, "in_file")
    workflow.connect(inputnode, "bold_mask_std", applymask, "mask_file")

    #
    merge = pe.Node(
        niu.Merge(2), name="merge"
    )
    workflow.connect(applymask, "out_file", merge, "in1")
    workflow.connect(inputnode, "confounds", merge, "in2")

    #
    workflow.connect(merge, "out", outputnode, "files")
    workflow.connect(inputnode, "bold_mask_std", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    return workflow
