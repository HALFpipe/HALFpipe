# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import afni

from .memory import MemoryCalculator


def init_smooth_wf(fwhm=None, memcalc=MemoryCalculator(), name="smooth_wf"):
    """
    Smooths a volume within a mask while correcting for the mask edge
    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(fields=["in_file", "mask_file", "fwhm"]),
        name="inputnode",
    )

    if fwhm is not None:
        assert isinstance(fwhm, float)
        inputnode.inputs.fwhm = fwhm

    smooth = pe.Node(
        afni.BlurInMask(preserve=True, float_out=True, out_file="blur.nii"), name="smooth"
    )

    workflow.connect(
        [
            (
                inputnode,
                smooth,
                [("in_file", "in_file"), ("mask_file", "mask"), ("fwhm", "fwhm")],
            ),
        ]
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(fields=["out_file"]), name="outputnode"
    )

    workflow.connect(smooth, "out_file", outputnode, "out_file")

    return workflow
