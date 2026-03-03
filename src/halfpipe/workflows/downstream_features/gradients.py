# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Literal, Sequence

from fmriprep import config
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from niworkflows.interfaces.utility import KeySelect

from ...interfaces.gradients import Gradients
from ...interfaces.image_maths.resample import Resample
from ...interfaces.reports.vals import CalcMean
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.extract import ExtractFromResultdict
from ...interfaces.result.filter import FilterResultdicts
from ...interfaces.result.make import MakeResultdicts
from ...model.downstream_feature import DownstreamFeature
from ...utils.format import format_workflow
from ..memory import MemoryCalculator

##############
# DRAFT CODE #
##############
# This code is a draft to implement brainspace gradients in HALFpipe
# TODO connect w/ atlas_based_connectivity wf
# TODO check outputs/run in halfpipe


def _broadcast_references(
    atlas_names: list[str],
    map_names: list[str],
) -> tuple[list[str], list[str]]:
    import itertools

    pairs = itertools.product(atlas_names, map_names)
    atlas_names, map_names = map(list, zip(*pairs, strict=True))

    return atlas_names, map_names


def init_gradients_wf(
    workdir: str | Path,
    downstream_feature: DownstreamFeature,
    map_files: Sequence[Path | str] | None = None,
    map_spaces: Sequence[Literal["MNI152NLin6Asym", "MNI152NLin2009cAsym"]] | None = None,
    memcalc: MemoryCalculator | None = None,
) -> pe.Workflow:
    """
    Create workflow for gradients. This workflow operates on an
    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc

    name = f"{format_workflow(downstream_feature.name)}_wf"
    workflow = pe.Workflow(name=name)

    ###################
    # SETUP I/O NODES #
    ###################
    # input node fields go into an identity interface that means the node does nothing to the values
    # here define all the inputs that will go through workflow
    # inputs will come from two places:
    # entries to Spec file/UI input via the Feature
    # things that were computed by halfpipe from another node
    inputnode = pe.Node(
        niu.IdentityInterface(
            # Adding a field here means also adding it in model > tags > resultdict.py (validates allowed tags)
            fields=[
                "map_names",
                "map_files",
                "map_spaces",
                # this will come from atlas-based connectivity workflow
                "resultdicts",
                "atlas_names",  # corresponds w feature atlases
                "atlas_files",  # corresponds w input spec atlas_file (why plural here? map node possible?)
                "atlas_spaces",
                # gradients params
                "approach",
                "kernel",
                "n_iter",
                "alignment",
                "sparsity",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    inputnode.inputs.approach = downstream_feature.approach
    inputnode.inputs.kernel = downstream_feature.kernel
    inputnode.inputs.n_iter = downstream_feature.n_iter
    inputnode.inputs.alignment = downstream_feature.alignment
    inputnode.inputs.sparsity = downstream_feature.sparsity

    inputnode.inputs.map_names = downstream_feature.maps
    inputnode.inputs.map_files = map_files
    inputnode.inputs.map_spaces = map_spaces

    #######################################
    # Extract connectivity matrices
    #######################################
    filter_resultdicts = pe.Node(
        interface=FilterResultdicts(require_one_of_images=["matrix"]),
        name="filter_resultdicts",
    )
    workflow.connect(inputnode, "resultdicts", filter_resultdicts, "in_dicts")
    extract_from_resultdict = pe.MapNode(
        ExtractFromResultdict(keys=["matrix", "atlas"]),
        iterfield="indict",
        allow_undefined_iterfield=True,
        name="extract_from_resultdict",
    )
    workflow.connect(filter_resultdicts, "resultdicts", extract_from_resultdict, "indict")

    #######################################
    # Calculate reference matrices
    #######################################
    broadcast_references = pe.Node(
        niu.Function(
            input_names=["atlas", "map_names"],
            output_names=["atlas", "map_names"],
            function=_broadcast_references,
        ),
        name="broadcast_references",
    )
    workflow.connect(extract_from_resultdict, "atlas", broadcast_references, "atlas")
    workflow.connect(inputnode, "map_names", broadcast_references, "map_names")

    atlas_select = pe.MapNode(
        KeySelect(fields=["atlas_file", "atlas_space"]),
        iterfield="key",
        name="atlas_select",
    )
    workflow.connect(broadcast_references, "atlas", atlas_select, "key")
    workflow.connect(inputnode, "atlas_names", atlas_select, "keys")
    workflow.connect(inputnode, "atlas_files", atlas_select, "atlas_file")
    workflow.connect(inputnode, "atlas_spaces", atlas_select, "atlas_space")

    map_select = pe.MapNode(
        KeySelect(fields=["map_file", "map_space"]),
        iterfield="key",
        name="map_select",
    )
    workflow.connect(broadcast_references, "map", map_select, "key")
    workflow.connect(inputnode, "map_names", map_select, "keys")
    workflow.connect(inputnode, "map_files", map_select, "atlas_file")
    workflow.connect(inputnode, "map_spaces", map_select, "atlas_space")

    resample = pe.MapNode(
        Resample(interpolation="MultiLabel", lazy=True),
        name="resample",
        iterfield=["input_image", "input_space"],
        n_procs=config.nipype.omp_nthreads,
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(atlas_select, "atlas_file", resample, "input_image")
    workflow.connect(atlas_select, "atlas_space", resample, "input_space")
    workflow.connect(map_select, "map_file", resample, "reference_image")
    workflow.connect(map_select, "map_space", resample, "reference_space")

    calcmean = pe.MapNode(
        CalcMean(),
        iterfield=["in_file", "parcellation"],
        name="calcmean",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(map_select, "map_file", calcmean, "in_file")
    workflow.connect(resample, "output_image", calcmean, "parcellation")

    # how to know what keys are needed/wanted?
    # here adding new keys to resultdict
    make_resultdicts = pe.Node(
        MakeResultdicts(
            tagkeys=[
                "downstream_feature",
                "map",
            ],  # tag keys go to filename (needs to be changed in model.tags.resultdict.py)
            imagekeys=["lambdas", "gradients", "aligned"],  # 'aligned' is an optional output so this might be wrong way
        ),
        name="make_resultdicts",
    )
    make_resultdicts.inputs.downstream_feature = downstream_feature.name

    # Connect inputnode values to relevant make_resultdicts outputs
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")

    # TODO do we care to connect all the feature inputs to make_resultdicts?
    #   e.g. under metadata keys for record keeping? (no for now)

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=workdir), name="resultdict_datasink")
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #######################################
    # CONNECT I/O NODES W/ GRADIENTS NODE #
    #######################################
    gradientsnode = pe.Node(
        Gradients(),
        name="gradients",
        mem_gb=memcalc.series_std_gb,
    )

    # connect inputnode values
    workflow.connect(inputnode, "n_components", gradientsnode, "n_components")
    workflow.connect(inputnode, "approach", gradientsnode, "approach")
    workflow.connect(inputnode, "kernel", gradientsnode, "kernel")
    workflow.connect(inputnode, "random_state", gradientsnode, "random_state")
    workflow.connect(inputnode, "alignment", gradientsnode, "alignment")
    workflow.connect(inputnode, "correlation_matrix", gradientsnode, "correlation_matrix")
    workflow.connect(inputnode, "gamma", gradientsnode, "gamma")
    workflow.connect(inputnode, "sparsity", gradientsnode, "sparsity")
    workflow.connect(inputnode, "n_iter", gradientsnode, "n_iter")
    workflow.connect(inputnode, "reference", gradientsnode, "reference")

    # connect resultdicts (how does this interact/correspond w the dictionary tags?)
    workflow.connect(gradientsnode, "lambdas", make_resultdicts, "lambdas")
    workflow.connect(gradientsnode, "gradients", make_resultdicts, "gradients")
    workflow.connect(gradientsnode, "aligned", make_resultdicts, "aligned")

    return workflow
