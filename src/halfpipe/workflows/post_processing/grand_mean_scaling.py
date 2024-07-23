# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from ...interfaces.grand_mean_scaling import GrandMeanScaling
from ..memory import MemoryCalculator


def init_grand_mean_scaling_wf(
    mean: float | None = None,
    memcalc: MemoryCalculator | None = None,
    name: str | None = None,
    suffix: str | None = None,
):
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    if name is None:
        if mean is not None:
            mean = float(mean)
            name = f"grand_mean_scaling_{int(mean):d}_wf"
        else:
            name = "grand_mean_scaling_wf"
    if suffix is not None:
        name = f"{name}_{suffix}"

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "mean", "vals"]),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["files", "mask", "vals"]), name="outputnode")

    workflow.connect(inputnode, "mask", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    if mean is not None:
        inputnode.inputs.mean = float(mean)

    grand_mean_scaling = pe.Node(GrandMeanScaling(), name="grand_mean_scaling", mem_gb=2 * memcalc.series_std_gb)
    workflow.connect(inputnode, "files", grand_mean_scaling, "files")
    workflow.connect(inputnode, "mask", grand_mean_scaling, "mask")
    workflow.connect(inputnode, "mean", grand_mean_scaling, "mean")

    workflow.connect(grand_mean_scaling, "files", outputnode, "files")

    return workflow
