# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl
from nipype.interfaces import afni

from .memory import MemoryCalculator


def init_temporalfilter_wf(temporal_filter_width, repetition_time,
                           name="temporalfilter", memcalc=MemoryCalculator()):
    """
    create a workflow for temporal filtering of functional data based on
    gaussian smoothing implemented by FSLMATHS

    :param temporal_filter_width: width of the remporal filter in seconds
    :param repetition_time: repetition time of the input volume
    :param name: workflow name (Default value = "temporalfilter")

    """

    # the workflow
    workflow = pe.Workflow(name=name)

    # only input is the bold image to be filtered
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file"]),
        name="inputnode"
    )

    # only output is the filtered bold image
    outputnode = pe.Node(niu.IdentityInterface(
        fields=["filtered_file", "highpass_file"]),
        name="outputnode"
    )

    # prepare operand string for FSLMATHS
    highpass_operand = "-bptf %.10f -1" % \
                       (temporal_filter_width / (2.0 * repetition_time))

    # node that calls FSLMATHS to actually do the temporal filtering
    highpass = pe.Node(
        interface=fsl.ImageMaths(
            op_string=highpass_operand, suffix="_tempfilt"),
        name="highpass",
        mem_gb=memcalc.series_std_gb
    )

    # temporal filtering also demeans the image, which is not desired.
    # Therefore, we add the mean of the original image back in.
    meanfunc = pe.Node(
        interface=fsl.ImageMaths(
            op_string="-Tmean", suffix="_mean"),
        name="meanfunc",
        mem_gb=memcalc.series_std_gb
    )
    addmean = pe.Node(
        interface=fsl.BinaryMaths(
            operation="add"),
        name="addmean",
        mem_gb=memcalc.series_std_gb
    )

    workflow.connect([
        (inputnode, highpass, [
            ("bold_file", "in_file")
        ]),
        (inputnode, meanfunc, [
            ("bold_file", "in_file")
        ]),
        (highpass, outputnode, [
            ("out_file", "highpass_file")
        ]),
        (highpass, addmean, [
            ("out_file", "in_file")
        ]),
        (meanfunc, addmean, [
            ("out_file", "operand_file")
        ]),
        (addmean, outputnode, [
            ("out_file", "filtered_file")
        ])
    ])

    return workflow


def init_bandpass_wf(repetition_time, highpass=0.009, lowpass=0.08,
                     name="bandpass"):
    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the regression files
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file"]),
        name="inputnode"
    )

    # filtering
    bandpass = pe.Node(
        interface=afni.Bandpass(),
        name="bandpass_filtering"
    )
    bandpass.inputs.lowpass = lowpass
    bandpass.inputs.highpass = highpass
    bandpass.inputs.tr = repetition_time
    bandpass.inputs.outputtype = "NIFTI_GZ"

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["filtered_file"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, bandpass, [
            ("bold_file", "in_file"),
            ("mask_file", "mask"),
        ]),
        (bandpass, outputnode, [
            ("out_file", "filtered_file"),
        ]),
    ])

    return workflow
