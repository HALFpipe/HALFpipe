# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import afni

from ..smooth import init_smooth_wf
from .zscore import init_zscore_wf

from ..memory import MemoryCalculator
from ...spec import (
    Tags,
    Analysis,
    BandPassFilteredTag,
    ConfoundsRemovedTag,
    SmoothedTag,
    GrandMeanScaledTag,
)
from ...interface import MakeResultdicts


def init_reho_wf(analysis=None, memcalc=MemoryCalculator()):
    """
    create a workflow to do ReHo

    """

    assert isinstance(analysis, Analysis)
    assert isinstance(analysis.tags, Tags)

    # make bold file variant specification
    varianttupls = [("space", analysis.tags.space)]
    if analysis.tags.grand_mean_scaled is not None:
        assert isinstance(analysis.tags.grand_mean_scaled, GrandMeanScaledTag)
        varianttupls.append(analysis.tags.grand_mean_scaled.as_tupl())
    if analysis.tags.band_pass_filtered is not None:
        assert isinstance(analysis.tags.band_pass_filtered, BandPassFilteredTag)
        varianttupls.append(analysis.tags.band_pass_filtered.as_tupl())
    if analysis.tags.confounds_removed is not None:
        assert isinstance(analysis.tags.confounds_removed, ConfoundsRemovedTag)
        varianttupls.append(analysis.tags.confounds_removed.as_tupl())

    boldfilevariant = (("bold_file",), tuple(varianttupls))

    assert analysis.name is not None
    workflow = pe.Workflow(name=f"{analysis.name}_analysis_wf")

    inputnode = pe.Node(
        interface=niu.IdentityInterface(fields=["bold_file", "mask_file", "metadata"]),
        name="inputnode",
    )

    reho = pe.Node(
        interface=afni.ReHo(neighborhood="vertices", out_file="reho.nii"),
        name="reho",
        mem_gb=memcalc.series_std_gb * 2,
    )
    workflow.connect([(inputnode, reho, [("bold_file", "in_file"), ("mask_file", "mask_file")])])

    endpoint = (reho, "out_file")
    if analysis.tags.smoothed is not None:
        assert isinstance(analysis.tags.smoothed, SmoothedTag)
        if not np.isclose(analysis.tags.smoothed.fwhm, 0):
            smooth_workflow = init_smooth_wf(fwhm=analysis.tags.smoothed.fwhm)
            workflow.connect(inputnode, "mask_file", smooth_workflow, "inputnode.mask_file")
            workflow.connect(*endpoint, smooth_workflow, "inputnode.in_file")
            endpoint = (smooth_workflow, "outputnode.out_file")

    zscore_workflow = init_zscore_wf()
    workflow.connect(inputnode, "mask_file", zscore_workflow, "inputnode.mask_file")
    workflow.connect(*endpoint, zscore_workflow, "inputnode.in_file")

    outputnode = pe.Node(
        interface=MakeResultdicts(
            keys=["firstlevelanalysisname", "firstlevelfeaturename", "stat", "mask_file"]
        ),
        name="outputnode",
    )
    outputnode.inputs.firstlevelanalysisname = analysis.name
    outputnode.inputs.firstlevelfeaturename = "reho"
    workflow.connect(
        [(inputnode, outputnode, [("metadata", "basedict"), ("mask_file", "mask_file")],)]
    )
    workflow.connect(zscore_workflow, "outputnode.out_file", outputnode, "stat")

    return workflow, (boldfilevariant,)
