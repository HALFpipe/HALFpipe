# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu

from ...interface import GrandMeanScaling
from ..memory import MemoryCalculator


def init_grand_mean_scaling_wf(mean=None, memcalc=MemoryCalculator(), name=None, suffix=None):
    """

    """
    if name is None:
        if mean is not None:
            mean = float(mean)
            name = f"grand_mean_scaling_{int(mean):d}_wf"
        else:
            name = f"grand_mean_scaling_wf"
    if suffix is not None:
        name = f"{name}_{suffix}"

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "mean"]), name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["files", "mask"]), name="outputnode")

    workflow.connect(inputnode, "mask", outputnode, "mask")

    if mean is not None:
        inputnode.inputs.mean = float(mean)

    grandmeanscaling = pe.Node(
        GrandMeanScaling(), name="grandmeanscaling"
    )
    workflow.connect(inputnode, "files", grandmeanscaling, "files")
    workflow.connect(inputnode, "mask", grandmeanscaling, "mask")
    workflow.connect(inputnode, "mean", grandmeanscaling, "mean")

    workflow.connect(grandmeanscaling, "files", outputnode, "files")

    return workflow
