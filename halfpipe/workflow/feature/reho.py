# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import afni

from ..memory import MemoryCalculator
from ...utils import formatlikebids
from ...interface import MakeResultdicts, ResultdictDatasink, ZScore, BlurInMask


def init_reho_wf(workdir=None, feature=None, fwhm=None, memcalc=MemoryCalculator()):
    """
    create a workflow to do ReHo

    """
    if feature is not None:
        name = f"{formatlikebids(feature.name)}"
    else:
        name = "reho"
    if fwhm is not None:
        name = f"{name}_{int(float(fwhm) * 1e3):d}"
    name = f"{name}_wf"
    workflow = pe.Workflow(name=name)

    # input
    inputnode = pe.Node(
        niu.IdentityInterface(fields=["tags", "bold", "mask", "fwhm"]), name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    if fwhm is not None:
        inputnode.inputs.fwhm = float(fwhm)

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(imagekeys=["reho"]), name="make_resultdicts", run_without_submitting=True
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    reho = pe.Node(
        interface=afni.ReHo(neighborhood="vertices", out_file="reho.nii"),
        name="reho",
        mem_gb=memcalc.series_std_gb * 2,
    )
    workflow.connect(inputnode, "bold", reho, "in_file")
    workflow.connect(inputnode, "mask", reho, "mask_file")

    #
    smooth = pe.Node(
        BlurInMask(preserve=True, float_out=True, out_file="blur.nii.gz"), name="smooth"
    )
    workflow.connect(reho, "out_file", smooth, "in_file")
    workflow.connect(inputnode, "mask", smooth, "mask")
    workflow.connect(inputnode, "fwhm", smooth, "fwhm")

    zscore = pe.Node(ZScore(), name="zscore", mem_gb=memcalc.volume_std_gb)
    workflow.connect(smooth, "out_file", zscore, "in_file")
    workflow.connect(inputnode, "mask", zscore, "mask")

    workflow.connect(zscore, "out_file", make_resultdicts, "reho")

    return workflow
