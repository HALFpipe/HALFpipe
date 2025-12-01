# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Literal, Sequence

from fmriprep import config
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from halfpipe.interfaces.gift import GicaCmd

from ...interfaces.image_maths.resample import Resample
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.make import MakeResultdicts
from ...model.feature import Feature
from ...utils.format import format_workflow
from ..configurables import configurables
from ..constants import Constants
from ..memory import MemoryCalculator


def init_gig_ica_wf(
    workdir: str | Path,
    feature: Feature | None = None,
    map_files: Sequence[Path | str] | None = None,
    map_spaces: Sequence[str] | None = None,
    space: Literal["standard", "native"] = "standard",
    memcalc: MemoryCalculator | None = None,
) -> pe.Workflow:
    """
    create a workflow to calculate a group information guided ICA (GIG-ICA)
    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    if feature is not None:
        name = f"{format_workflow(feature.name)}_wf"
    else:
        name = "gig_ica_wf"
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "tags",
                "vals",
                "metadata",
                "bold",
                "mask",
                "confounds_selected",
                "map_names",
                "map_files",
                "map_spaces",
                # resampling to native space
                "std2anat_xfm",
                "bold_ref_anat",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    if feature is not None:
        inputnode.inputs.map_names = feature.maps
    if map_files is not None:
        inputnode.inputs.map_files = map_files
    if map_spaces is not None:
        inputnode.inputs.map_spaces = map_spaces

    # Set up the datasink
    make_resultdicts = pe.Node(
        MakeResultdicts(
            tagkeys=["feature", "map"],
            imagekeys=["effect", "mask", "timeseries", "correlation_matrix"],
            metadatakeys=["sources"],
        ),
        name="make_resultdicts",
    )

    if feature is not None:
        make_resultdicts.inputs.feature = feature.name
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "map_names", make_resultdicts, "map")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")

    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir),
        name="resultdict_datasink",
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    # Resample the maps to standard or native space
    resample_maps = pe.MapNode(
        Resample(interpolation="LanczosWindowedSinc", lazy=True),
        name="resample_maps",
        iterfield=["input_image", "input_space"],
        n_procs=config.nipype.omp_nthreads,
        mem_gb=memcalc.series_std_gb,
    )
    if space == "standard":
        resample_maps.inputs.reference_space = Constants.reference_space
        resample_maps.inputs.reference_res = configurables.reference_res
    elif space == "native":
        workflow.connect(inputnode, "std2anat_xfm", resample_maps, "transforms")
        workflow.connect(inputnode, "bold_ref_anat", resample_maps, "reference_image")
    workflow.connect(inputnode, "map_files", resample_maps, "input_image")
    workflow.connect(inputnode, "map_spaces", resample_maps, "input_space")

    # Call gica_cmd to perform the calculation
    gica_cmd = pe.MapNode(
        GicaCmd(modality="fmri", algorithm="moo-icar"),
        name="gica_cmd",
        iterfield=["templates"],
        mem_gb=memcalc.series_std_gb * 5,
    )
    workflow.connect(resample_maps, "output_image", gica_cmd, "templates")
    workflow.connect(inputnode, "bold", gica_cmd, "data")
    workflow.connect(inputnode, "mask", gica_cmd, "mask")

    workflow.connect(gica_cmd, "components", make_resultdicts, "effect")
    workflow.connect(gica_cmd, "mask", make_resultdicts, "mask")

    workflow.connect(gica_cmd, "timecourses", make_resultdicts, "timeseries")
    workflow.connect(gica_cmd, "fnc_corrs", make_resultdicts, "correlation_matrix")

    return workflow
