# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu

from .zscore import init_zscore_wf
from ...interface import ReHo

from ..memory import MemoryCalculator


def init_reho_wf(name="reho", memcalc=MemoryCalculator()):
    """
    create a workflow to do ReHo

    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "mask_file", "confounds"]),
        name="inputnode"
    )

    reho = pe.Node(
        interface=ReHo(),
        name="reho",
        mem_gb=memcalc.series_std_gb*2
    )
    reho.inputs.cluster_size = 27

    zscore_workflow = init_zscore_wf()

    # outputs are cope and zstat
    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["reho_stat"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, reho, [
            ("bold_file", "in_file"),
            ("mask_file", "mask_file"),
        ]),
        (reho, zscore_workflow, [
            ("out_file", "inputnode.in_file"),
        ]),
        (inputnode, zscore_workflow, [
            ("mask_file", "inputnode.mask_file"),
        ]),
        (zscore_workflow, outputnode, [
            ("outputnode.out_file", "reho_stat"),
        ]),
    ])

    outnames = ["reho"]

    outfields = ["stat"]

    return workflow, outnames, outfields
