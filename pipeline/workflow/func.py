from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl
from nipype.algorithms import confounds as nac

from mriqc.interfaces import viz


def init_temporalfilter_wf(temporal_filter_width, repetition_time, name="temporalfilter"):
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
        fields=["bold_file", ""]),
        name="inputnode"
    )

    # only output is the filtered bold image
    outputnode = pe.Node(niu.IdentityInterface(
        fields=["filtered_file"]),
        name="outputnode"
    )

    # prepare operand string for FSLMATHS
    highpass_operand = "-bptf %.10f -1" % \
                       (temporal_filter_width / (2.0 * repetition_time))

    # node that calls FSLMATHS to actually do the temporal filtering
    highpass = pe.Node(
        interface=fsl.ImageMaths(
            op_string=highpass_operand, suffix="_tempfilt"),
        name="highpass"
    )

    # temporal filtering also demeans the image, which is not desired. Therefore, 
    # we add the mean of the original image back in.
    meanfunc = pe.Node(
        interface=fsl.ImageMaths(
            op_string="-Tmean", suffix="_mean"),
        name="meanfunc"
    )
    addmean = pe.Node(
        interface=fsl.BinaryMaths(
            operation="add"),
        name="addmean"
    )

    workflow.connect([
        (inputnode, highpass, [
            ("bold_file", "in_file")
        ]),
        (inputnode, meanfunc, [
            ("bold_file", "in_file")
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


def init_tsnr_wf(name="tsnr"):
    """
    create a workflow to calculate the temporal signal-to-noise
    ratio of a functional image

    :param name: workflow name (Default value = "tsnr")

    """
    workflow = pe.Workflow(name=name)

    # only input is the bold image
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file"]),
        name="inputnode"
    )

    # output is an image file for display in the qualitycheck web page
    outputnode = pe.Node(niu.IdentityInterface(
        fields=["report_file"]),
        name="outputnode"
    )

    # actually calculate the tsnr image
    tsnr = pe.Node(
        interface=nac.TSNR(),
        name="compute_tsnr")

    # plot the resulting image as a mosaic
    mosaic_stddev = pe.Node(
        interface=viz.PlotMosaic(
            out_file="plot_func_stddev_mosaic2_stddev.svg",
            cmap="viridis"),
        name="plot_mosaic")

    workflow.connect([
        (inputnode, tsnr, [
            ("bold_file", "in_file")
        ]),
        (tsnr, mosaic_stddev, [
            ("tsnr_file", "in_file")
        ]),
        (mosaic_stddev, outputnode, [
            ("out_file", "report_file")
        ])
    ])

    return workflow
