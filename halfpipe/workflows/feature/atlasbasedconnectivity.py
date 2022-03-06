# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from nipype.algorithms import confounds as nac
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from ...interfaces.connectivity import ConnectivityMeasure
from ...interfaces.imagemaths.resample import Resample
from ...interfaces.report.vals import CalcMean
from ...interfaces.resultdict.datasink import ResultdictDatasink
from ...interfaces.resultdict.make import MakeResultdicts
from ...utils.format import format_workflow
from ..constants import constants
from ..memory import MemoryCalculator


def init_atlasbasedconnectivity_wf(
    workdir: str | Path,
    feature=None,
    atlas_files=None,
    atlas_spaces=None,
    memcalc=MemoryCalculator.default(),
):
    """
    create workflow for brainatlas

    """
    if feature is not None:
        name = f"{format_workflow(feature.name)}_wf"
    else:
        name = "atlasbasedconnectivity_wf"
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "tags",
                "vals",
                "metadata",
                "bold",
                "mask",
                "repetition_time",
                "atlas_names",
                "atlas_files",
                "atlas_spaces",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["resultdicts"]), name="outputnode"
    )

    min_region_coverage = 1
    if feature is not None:
        inputnode.inputs.atlas_names = feature.atlases
        if hasattr(feature, "min_region_coverage"):
            min_region_coverage = feature.min_region_coverage

    if atlas_files is not None:
        inputnode.inputs.atlas_files = atlas_files

    if atlas_spaces is not None:
        inputnode.inputs.atlas_spaces = atlas_spaces

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(
            tagkeys=["feature", "atlas"],
            imagekeys=["timeseries", "covariance_matrix", "correlation_matrix"],
            metadatakeys=[
                "sources",
                "sampling_frequency",
                "mean_atlas_tsnr",
                "coverage",
            ],
            nobroadcastkeys=["mean_atlas_tsnr", "coverage"],
        ),
        name="make_resultdicts",
    )
    if feature is not None:
        make_resultdicts.inputs.feature = feature.name
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
    workflow.connect(inputnode, "atlas_names", make_resultdicts, "atlas")
    workflow.connect(
        inputnode, "repetition_time", make_resultdicts, "sampling_frequency"
    )

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    reference_dict = dict(
        reference_space=constants.reference_space, reference_res=constants.reference_res
    )
    resample = pe.MapNode(
        Resample(interpolation="MultiLabel", **reference_dict),
        name="resample",
        iterfield=["input_image", "input_space"],
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "atlas_files", resample, "input_image")
    workflow.connect(inputnode, "atlas_spaces", resample, "input_space")

    #
    connectivitymeasure = pe.MapNode(
        ConnectivityMeasure(
            background_label=0, min_region_coverage=min_region_coverage
        ),
        name="connectivitymeasure",
        iterfield=["atlas_file"],
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "bold", connectivitymeasure, "in_file")
    workflow.connect(inputnode, "mask", connectivitymeasure, "mask_file")
    workflow.connect(resample, "output_image", connectivitymeasure, "atlas_file")

    workflow.connect(connectivitymeasure, "time_series", make_resultdicts, "timeseries")
    workflow.connect(
        connectivitymeasure, "covariance", make_resultdicts, "covariance_matrix"
    )
    workflow.connect(
        connectivitymeasure, "correlation", make_resultdicts, "correlation_matrix"
    )
    workflow.connect(
        connectivitymeasure, "region_coverage", make_resultdicts, "coverage"
    )

    #
    tsnr = pe.Node(interface=nac.TSNR(), name="tsnr", mem_gb=memcalc.series_std_gb)
    workflow.connect(inputnode, "bold", tsnr, "in_file")

    calcmean = pe.MapNode(
        CalcMean(),
        iterfield="parcellation",
        name="calcmean",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(resample, "output_image", calcmean, "parcellation")
    workflow.connect(inputnode, "mask", calcmean, "mask")
    workflow.connect(tsnr, "tsnr_file", calcmean, "in_file")

    workflow.connect(calcmean, "mean", make_resultdicts, "mean_atlas_tsnr")

    return workflow
