# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import afni

from .zscore import init_zscore_wf

from ..memory import MemoryCalculator


def init_alff_wf(name="alff", memcalc=MemoryCalculator()):
    """
    Calculate Amplitude of low frequency oscillations(ALFF) and
    fractional ALFF maps

    Returns
    -------
    alff_workflow : workflow object
        ALFF workflow

    Notes
    -----
    Adapted from
    <https://github.com/FCP-INDI/C-PAC/blob/master/CPAC/alff/alff.py>

    Workflow Inputs::
        inputnode.rest_res : string (existing nifti file)
            Nuisance signal regressed functional image
        inputnode.rest_mask : string (existing nifti file)
            A mask volume(derived by dilating the motion corrected
            functional volume) in native space
    Workflow Outputs::
        outputnode.alff_cope : string (nifti file)
            outputs image containing the sum of the amplitudes in
            the low frequency band
        outputnode.falff_cope : string (nifti file)
            outputs image containing the sum of the amplitudes in the
            low frequency band divided by the amplitude of the total frequency
        outputnode.alff_Z_img : string (nifti file)
            outputs image containing Normalized ALFF Z scores across
            full brain in native space
        outputnode.falff_Z_img : string (nifti file)
            outputs image containing Normalized fALFF Z scores across full
            brain in native space

    """

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "filtered_file", "mask_file"]
        ),
        name="inputnode",
    )

    # standard deviation over frequency
    stddev_filtered = pe.Node(
        interface=afni.TStat(), name="stddev_filtered", mem_gb=memcalc.series_std_gb
    )
    stddev_filtered.inputs.outputtype = "NIFTI_GZ"
    stddev_filtered.inputs.options = "-stdev"

    # standard deviation of the unfiltered nuisance corrected image
    stddev_unfiltered = pe.Node(
        interface=afni.TStat(), name="stddev_unfiltered", mem_gb=memcalc.series_std_gb
    )
    stddev_unfiltered.inputs.outputtype = "NIFTI_GZ"
    stddev_unfiltered.inputs.options = "-stdev"

    falff = pe.Node(interface=afni.Calc(), name="falff", mem_gb=memcalc.volume_std_gb)
    falff.inputs.args = "-float"
    falff.inputs.expr = "(1.0*bool(a))*((1.0*b)/(1.0*c))"
    falff.inputs.outputtype = "NIFTI_GZ"

    alff_zscore_workflow = init_zscore_wf("alff_zscore")

    falff_zscore_workflow = init_zscore_wf("falff_zscore")

    outputnode = pe.Node(
        interface=niu.IdentityInterface(fields=["alff_stat", "falff_stat"]),
        name="outputnode",
    )

    workflow.connect(
        [
            (
                inputnode,
                stddev_unfiltered,
                [("bold_file", "in_file"), ("mask_file", "mask"),],
            ),
            (
                inputnode,
                stddev_filtered,
                [("filtered_file", "in_file"), ("mask_file", "mask"),],
            ),
            (inputnode, falff, [("mask_file", "in_file_a"),]),
            (stddev_filtered, falff, [("out_file", "in_file_b"),]),
            (stddev_unfiltered, falff, [("out_file", "in_file_c"),]),
            (inputnode, alff_zscore_workflow, [("mask_file", "inputnode.mask_file"),]),
            (
                stddev_filtered,
                alff_zscore_workflow,
                [("out_file", "inputnode.in_file"),],
            ),
            (inputnode, falff_zscore_workflow, [("mask_file", "inputnode.mask_file"),]),
            (falff, falff_zscore_workflow, [("out_file", "inputnode.in_file"),]),
            (alff_zscore_workflow, outputnode, [("outputnode.out_file", "alff_stat"),]),
            (
                falff_zscore_workflow,
                outputnode,
                [("outputnode.out_file", "falff_stat"),],
            ),
        ]
    )

    outnames = ["alff", "falff"]

    outfields = ["stat"]

    return workflow, outnames, outfields
