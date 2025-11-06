# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

#from pathlib import Path
#from typing import Literal, Sequence

#from nipype.algorithms import confounds as nac
#from nipype.interfaces import utility as niu
#from nipype.pipeline import engine as pe

#from ...interfaces.result.datasink import ResultdictDatasink
#from ...interfaces.result.make import MakeResultdicts
#from ...utils.format import format_workflow
#from ..constants import Constants
from ..memory import MemoryCalculator

from nipype import Node, Workflow
from ...interfaces.gradients import Gradients

from os.path import abspath

##############
# DRAFT CODE #
##############
# This code is a draft to implement brainspace gradients in HALFpipe
# TODO everything


def init_gradients_wf(
    workdir: str | Path,
    # These exist everywhere but I want them gone
    # feature: Feature | None = None,
    # what comes out of atlas_based_connectivity_wf ? how to pass inputs here
    memcalc: MemoryCalculator | None = None,
) -> pe.Workflow:
    """
    create workflow for gradients

    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc

    workflow = pe.Workflow(name="gadients_wf")

    ###################
    # SETUP I/O NODES #
    ###################

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "tags",
                "vals",
                "metadata",

                # gradients params
                "n_components",
                "approach",
                "kernel",
                "random_state",
                "alignment",
                "x",
                "gamma",
                "sparsity",
                "n_iter",
                "reference",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    #min_region_coverage = 1
    #if feature is not None:
    #    inputnode.inputs.atlas_names = feature.atlases
    #    if hasattr(feature, "min_region_coverage"):
    #        min_region_coverage = feature.min_region_coverage

    #if atlas_files is not None:
    #    inputnode.inputs.atlas_files = atlas_files

    #if atlas_spaces is not None:
    #    inputnode.inputs.atlas_spaces = atlas_spaces

    # how to know what keys are needed/wanted?
    make_resultdicts = pe.Node(
        MakeResultdicts(
            tagkeys=["feature", "atlas"], # ?
            imagekeys=["lambdas", "gradients", "aligned"], # 'aligned' is an optional output so this might be wrong way
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
    #if feature is not None:
    #    make_resultdicts.inputs.feature = feature.name

    # Connect inputnode values to relevant make_resultdicts outputs
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
    #workflow.connect(inputnode, "atlas_names", make_resultdicts, "atlas")
    #workflow.connect(inputnode, "repetition_time", make_resultdicts, "sampling_frequency")

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    #
    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=workdir), name="resultdict_datasink")
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    ##########################
    # NODES W/ WF INTERFACES #
    ##########################

    resample = pe.Node(
        Gradients(# input?
        ),
        name="gradients",
        mem_gb=memcalc.series_std_gb, # what does this do?
    )
    # connect inputnode values
    workflow.connect(inputnode, "n_components", gradients, "n_components")
    workflow.connect(inputnode, "approach", gradients, "approach")
    workflow.connect(inputnode, "kernel", gradients, "kernel")
    workflow.connect(inputnode, "random_state", gradients, "random_state")
    workflow.connect(inputnode, "alignment", gradients, "alignment")
    workflow.connect(inputnode, "x", gradients, "x")
    workflow.connect(inputnode, "gamma", gradients, "gamma")
    workflow.connect(inputnode, "sparsity", gradients, "sparsity")
    workflow.connect(inputnode, "n_iter", gradients, "n_iter")
    workflow.connect(inputnode, "reference", gradients, "reference")

    # connect resultdicts (how does this interact/correspond w the dictionary tags?)
    workflow.connect(gradients, "lambdas", make_resultdicts, "lambdas")
    workflow.connect(gradients, "gradients", make_resultdicts, "gradients")
    workflow.connect(gradients, "aligned", make_resultdicts, "aligned")

    return workflow
