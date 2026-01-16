# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Literal, Sequence

from nipype.algorithms import confounds as nac
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from ...interfaces.connectivity import ConnectivityMeasure
from ...interfaces.image_maths.resample import Resample
from ...interfaces.reports.vals import CalcMean
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.make import MakeResultdicts
from ...model.feature import Feature
from ...utils.format import format_workflow
from ..configurables import configurables
from ..constants import Constants
from ..memory import MemoryCalculator


def init_atlas_based_connectivity_wf(
    workdir: str | Path,
    feature: Feature | None = None,
    atlas_files: Sequence[Path | str] | None = None,
    atlas_spaces: Sequence[str] | None = None,
    space: Literal["standard", "native"] = "standard",
    memcalc: MemoryCalculator | None = None,
) -> pe.Workflow:
    """
    create workflow for brainatlas
    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    if feature is not None:
        name = f"{format_workflow(feature.name)}_wf"
    else:
        name = "atlas_based_connectivity_wf"
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "tags",  # dictionary keys to values
                "vals",  # fd_mean, etc.
                "metadata",  # repetition_time, etc.
                "bold",
                "mask",
                "repetition_time",
                "atlas_names",
                "atlas_files",
                "atlas_spaces",
                # resampling to native space
                "std2anat_xfm",
                "bold_ref_anat",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

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
    workflow.connect(inputnode, "repetition_time", make_resultdicts, "sampling_frequency")

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    #
    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=workdir), name="resultdict_datasink")
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    resample = pe.MapNode(
        Resample(interpolation="MultiLabel", lazy=True),
        name="resample",
        iterfield=["input_image", "input_space"],
        mem_gb=memcalc.series_std_gb,
    )
    if space == "standard":
        resample.inputs.reference_space = configurables.reference_space
        resample.inputs.reference_res = configurables.reference_res
    elif space == "native":
        workflow.connect(inputnode, "std2anat_xfm", resample, "transforms")
        workflow.connect(inputnode, "bold_ref_anat", resample, "reference_image")
    workflow.connect(inputnode, "atlas_files", resample, "input_image")
    workflow.connect(inputnode, "atlas_spaces", resample, "input_space")

    #
    connectivitymeasure = pe.MapNode(
        ConnectivityMeasure(background_label=0, min_region_coverage=min_region_coverage),
        name="connectivitymeasure",
        iterfield=["atlas_file"],
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "bold", connectivitymeasure, "in_file")
    workflow.connect(inputnode, "mask", connectivitymeasure, "mask_file")
    workflow.connect(resample, "output_image", connectivitymeasure, "atlas_file")

    workflow.connect(connectivitymeasure, "time_series", make_resultdicts, "timeseries")
    workflow.connect(connectivitymeasure, "covariance", make_resultdicts, "covariance_matrix")
    workflow.connect(connectivitymeasure, "correlation", make_resultdicts, "correlation_matrix")
    workflow.connect(connectivitymeasure, "region_coverage", make_resultdicts, "coverage")

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
