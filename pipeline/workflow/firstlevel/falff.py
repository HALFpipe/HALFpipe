# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import afni

from ..smooth import init_smooth_wf
from .zscore import init_zscore_wf
from ...interface import MakeResultdicts

from ..memory import MemoryCalculator
from ...spec import Tags, Analysis, BandPassFilteredTag, ConfoundsRemovedTag, SmoothedTag
from ...utils import first, onlyboldentitiesdict


def init_falff_wf(analysis=None, memcalc=MemoryCalculator()):
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

    assert isinstance(analysis, Analysis)
    assert isinstance(analysis.tags, Tags)

    # make bold file variant specification
    varianttupls_filtered = [("space", analysis.tags.space)]
    varianttupls_unfiltered = [("space", analysis.tags.space)]
    assert analysis.tags.band_pass_filtered is not None
    assert isinstance(analysis.tags.band_pass_filtered, BandPassFilteredTag)
    varianttupls_filtered.append(analysis.tags.band_pass_filtered.as_tupl())
    if analysis.tags.confounds_removed is not None:
        assert isinstance(analysis.tags.confounds_removed, ConfoundsRemovedTag)
        varianttupls_filtered.append(analysis.tags.confounds_removed.as_tupl())
        varianttupls_unfiltered.append(analysis.tags.confounds_removed.as_tupl())

    boldfilevariants = (
        (("bold_file_filtered",), tuple(varianttupls_filtered)),
        (("bold_file_unfiltered",), tuple(varianttupls_unfiltered)),
    )

    assert analysis.name is not None
    workflow = pe.Workflow(name=analysis.name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file_filtered", "bold_file_unfiltered", "mask_file", "metadata"]
        ),
        name="inputnode",
    )

    # standard deviation over frequency
    stddev_filtered = pe.Node(
        interface=afni.TStat(), name="stddev_filtered", mem_gb=memcalc.series_std_gb
    )
    stddev_filtered.inputs.outputtype = "NIFTI_GZ"
    stddev_filtered.inputs.options = "-stdev"
    workflow.connect(
        [
            (
                inputnode,
                stddev_filtered,
                [("bold_file_filtered", "in_file"), ("mask_file", "mask")],
            )
        ]
    )

    # standard deviation of the unfiltered nuisance corrected image
    stddev_unfiltered = pe.Node(
        interface=afni.TStat(), name="stddev_unfiltered", mem_gb=memcalc.series_std_gb
    )
    stddev_unfiltered.inputs.outputtype = "NIFTI_GZ"
    stddev_unfiltered.inputs.options = "-stdev"
    workflow.connect(
        [
            (
                inputnode,
                stddev_unfiltered,
                [("bold_file_unfiltered", "in_file"), ("mask_file", "mask")],
            )
        ]
    )

    falff = pe.Node(interface=afni.Calc(), name="falff", mem_gb=memcalc.volume_std_gb)
    falff.inputs.args = "-float"
    falff.inputs.expr = "(1.0*bool(a))*((1.0*b)/(1.0*c))"
    falff.inputs.outputtype = "NIFTI_GZ"
    workflow.connect(
        [
            (inputnode, falff, [("mask_file", "in_file_a")]),
            (stddev_filtered, falff, [("out_file", "in_file_b")]),
            (stddev_unfiltered, falff, [("out_file", "in_file_c")]),
        ]
    )

    alff_endpoint = (stddev_filtered, "out_file")
    falff_endpoint = (falff, "out_file")
    endpointlist = [("alff", alff_endpoint), ("falff", falff_endpoint)]
    endpointnames = list(map(first, endpointlist))

    mergeresults = pe.Node(interface=niu.Merge(2), name="mergeresults")
    for i, (name, endpoint) in enumerate(endpointlist):
        if analysis.tags.smoothed is not None:
            assert isinstance(analysis.tags.smoothed, SmoothedTag)
            if not np.isclose(analysis.tags.smoothed.fwhm, 0):
                smooth_workflow = init_smooth_wf(
                    fwhm=analysis.tags.smoothed.fwhm, name=f"{name}_smooth_wf", memcalc=memcalc
                )
                workflow.connect(
                    inputnode, "mask_file", smooth_workflow, "inputnode.mask_file"
                )
                workflow.connect(*endpoint, smooth_workflow, "inputnode.in_file")
                endpoint = (smooth_workflow, "outputnode.out_file")
        zscore_workflow = init_zscore_wf(name=f"{name}_zscore_wf", memcalc=memcalc)
        workflow.connect(inputnode, "mask_file", zscore_workflow, "inputnode.mask_file")
        workflow.connect(*endpoint, zscore_workflow, "inputnode.in_file")

        workflow.connect(zscore_workflow, "outputnode.out_file", mergeresults, f"in{i+1}")

    outputnode = pe.Node(
        interface=MakeResultdicts(
            keys=["analysisname", "firstlevelname", "stat", "mask_file"]
        ),
        name="outputnode",
    )
    outputnode.inputs.analysisname = analysis.name
    outputnode.inputs.firstlevelname = endpointnames
    workflow.connect(
        [
            (
                inputnode,
                outputnode,
                [(("metadata", onlyboldentitiesdict), "basedict"), ("mask_file", "mask_file")],
            )
        ]
    )
    workflow.connect(mergeresults, "out", outputnode, "stat")

    return workflow, boldfilevariants
