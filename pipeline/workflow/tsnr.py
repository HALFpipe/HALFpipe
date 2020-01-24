# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.algorithms import confounds as nac

from mriqc.interfaces import viz


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
