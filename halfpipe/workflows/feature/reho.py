# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu

from ...interfaces.fixes.reho import ReHo
from ...interfaces.imagemaths.lazy_blur import LazyBlurToFWHM
from ...interfaces.imagemaths.zscore import ZScore
from ...interfaces.resultdict.datasink import ResultdictDatasink
from ...interfaces.resultdict.make import MakeResultdicts
from ...utils.format import format_workflow
from ..memory import MemoryCalculator


def init_reho_wf(
    workdir: str | Path, feature=None, fwhm=None, memcalc=MemoryCalculator.default()
):
    """
    create a workflow to do ReHo

    """
    if feature is not None:
        name = f"{format_workflow(feature.name)}"
    else:
        name = "reho"
    if fwhm is not None:
        name = f"{name}_{int(float(fwhm) * 1e3):d}"
    name = f"{name}_wf"
    workflow = pe.Workflow(name=name)

    # input
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["tags", "vals", "metadata", "bold", "mask", "fwhm"]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["resultdicts"]), name="outputnode"
    )

    if fwhm is not None:
        inputnode.inputs.fwhm = float(fwhm)
    elif feature is not None and hasattr(feature, "smoothing"):
        inputnode.inputs.fwhm = feature.smoothing.get("fwhm")
    else:
        inputnode.inputs.fwhm = 0  # skip

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(tagkeys=["feature"], imagekeys=["reho", "mask"]),
        name="make_resultdicts",
    )
    if feature is not None:
        make_resultdicts.inputs.feature = feature.name
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
    workflow.connect(inputnode, "mask", make_resultdicts, "mask")

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    reho = pe.Node(
        interface=ReHo(neighborhood="vertices", out_file="reho.nii"),
        name="reho",
        mem_gb=memcalc.series_std_gb * 2,
    )
    workflow.connect(inputnode, "bold", reho, "in_file")
    workflow.connect(inputnode, "mask", reho, "mask_file")

    #
    smooth = pe.Node(LazyBlurToFWHM(outputtype="NIFTI_GZ"), name="smooth")
    workflow.connect(reho, "out_file", smooth, "in_file")
    workflow.connect(inputnode, "mask", smooth, "mask")
    workflow.connect(inputnode, "fwhm", smooth, "fwhm")

    zscore = pe.Node(ZScore(), name="zscore", mem_gb=memcalc.volume_std_gb)
    workflow.connect(smooth, "out_file", zscore, "in_file")
    workflow.connect(inputnode, "mask", zscore, "mask")

    workflow.connect(zscore, "out_file", make_resultdicts, "reho")

    return workflow
