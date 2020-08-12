# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.algorithms.modelgen as model

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ...interface import (
    ParseConditionFile,
    MakeResultdicts,
    FillNA,
    ResultdictDatasink,
    MakeDofVolume,
    MergeColumns,
    Unvest
)
from ...utils import firstfloat, firststr, formatlikebids, ravel

from ..memory import MemoryCalculator


def init_taskbased_wf(
    workdir=None,
    feature=None,
    condition_files=None,
    condition_units=None,
    memcalc=MemoryCalculator(),
):
    """
    create workflow to calculate a first level glm for task functional data
    """
    if feature is not None:
        name = f"{formatlikebids(feature.name)}_wf"
    else:
        name = "taskbased_wf"
    workflow = pe.Workflow(name=name)

    #
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "tags",
                "vals",
                "metadata",
                "bold",
                "mask",
                "repetition_time",
                "confounds_selected",
                "condition_names",
                "condition_files",
                "condition_units",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    if feature is not None:
        inputnode.inputs.condition_names = feature.conditions

    if condition_files is not None:
        inputnode.inputs.condition_files = condition_files

    if condition_units is not None:
        inputnode.inputs.condition_units = condition_units

    #
    make_resultdicts_a = pe.Node(
        MakeResultdicts(tagkeys=["feature"], imagekeys=["design_matrix", "contrast_matrix"]),
        name="make_resultdicts_a",
        run_without_submitting=True
    )
    if feature is not None:
        make_resultdicts_a.inputs.feature = feature.name
    workflow.connect(inputnode, "tags", make_resultdicts_a, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts_a, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts_a, "metadata")
    make_resultdicts_b = pe.Node(
        MakeResultdicts(
            tagkeys=["feature", "contrast"],
            imagekeys=["effect", "variance", "z", "dof", "mask"],
            metadatakeys=["sources"],
        ),
        name="make_resultdicts_b",
        run_without_submitting=True
    )
    if feature is not None:
        make_resultdicts_b.inputs.feature = feature.name
    workflow.connect(inputnode, "tags", make_resultdicts_b, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts_b, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts_b, "metadata")

    workflow.connect(make_resultdicts_b, "resultdicts", outputnode, "resultdicts")

    #
    merge_resultdicts = pe.Node(niu.Merge(2), name="merge_resultdicts")
    workflow.connect(make_resultdicts_a, "resultdicts", merge_resultdicts, "in1")
    workflow.connect(make_resultdicts_b, "resultdicts", merge_resultdicts, "in2")
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(merge_resultdicts, "out", resultdict_datasink, "indicts")

    # parse condition files into three (ordered) lists
    parseconditionfile = pe.Node(ParseConditionFile(), name="parseconditionfile", run_without_submitting=True)
    workflow.connect(inputnode, "condition_names", parseconditionfile, "condition_names")
    workflow.connect(inputnode, "condition_files", parseconditionfile, "in_any")

    fillna = pe.Node(FillNA(), name="fillna", run_without_submitting=True)
    workflow.connect(inputnode, "confounds_selected", fillna, "in_tsv")

    # first level model specification
    modelspec = pe.Node(model.SpecifyModel(), name="modelspec")
    workflow.connect(inputnode, "bold", modelspec, "functional_runs")
    workflow.connect(inputnode, "condition_units", modelspec, "input_units")
    workflow.connect(inputnode, "repetition_time", modelspec, "time_repetition")
    workflow.connect(fillna, "out_no_header", modelspec, "realignment_parameters")
    workflow.connect(parseconditionfile, "subject_info", modelspec, "subject_info")

    # transform contrasts dictionary to nipype list data structure
    contrasts = []
    if feature is not None:
        condition_names = feature.conditions
        for contrast in feature.contrasts:
            contrast_values = [contrast["values"].get(c, 0.0) for c in condition_names]
            contrasts.append(
                [contrast["name"], contrast["type"].upper(), condition_names, contrast_values]
            )

    # generate design from first level specification
    level1design = pe.Node(
        fsl.Level1Design(
            contrasts=contrasts,
            model_serial_correlations=True,
            bases={"dgamma": {"derivs": False}},
        ),
        name="level1design",
    )
    workflow.connect(inputnode, "repetition_time", level1design, "interscan_interval")
    workflow.connect(modelspec, "session_info", level1design, "session_info")

    # generate required input files for FILMGLS from design
    modelgen = pe.Node(fsl.FEATModel(), name="modelgen")
    workflow.connect([(level1design, modelgen, [(("fsf_files", firststr), "fsf_file")])])
    workflow.connect([(level1design, modelgen, [(("ev_files", ravel), "ev_files")])])

    # calculate range of image values to determine cutoff value
    stats = pe.Node(fsl.ImageStats(op_string="-R"), name="stats")
    workflow.connect(inputnode, "bold", stats, "in_file")
    cutoff = pe.Node(
        niu.Function(input_names=["obj"], output_names=["min_val"], function=firstfloat),
        name="cutoff",
    )
    workflow.connect(stats, "out_stat", cutoff, "obj")

    # actually estimate the first level model
    modelestimate = pe.Node(
        fsl.FILMGLS(smooth_autocorr=True, mask_size=5),
        name="modelestimate"
    )
    workflow.connect(inputnode, "bold", modelestimate, "in_file")
    workflow.connect(cutoff, "min_val", modelestimate, "threshold")
    workflow.connect(modelgen, "design_file", modelestimate, "design_file")
    workflow.connect(modelgen, "con_file", modelestimate, "tcon_file")

    # make dof volume
    makedofvolume = pe.Node(
        MakeDofVolume(), iterfield=["dof_file", "copes"], name="makedofvolume", run_without_submitting=True
    )
    workflow.connect(modelestimate, "copes", makedofvolume, "copes")
    workflow.connect(modelestimate, "dof_file", makedofvolume, "dof_file")

    workflow.connect(modelestimate, "copes", make_resultdicts_b, "effect")
    workflow.connect(modelestimate, "varcopes", make_resultdicts_b, "variance")
    workflow.connect(modelestimate, "zstats", make_resultdicts_b, "z")
    workflow.connect(makedofvolume, "out_file", make_resultdicts_b, "dof")
    workflow.connect(inputnode, "mask", make_resultdicts_b, "mask")

    #
    mergecolumnnames = pe.Node(niu.Merge(2), name="mergecolumnnames", run_without_submitting=True)
    mergecolumnnames.inputs.in1 = condition_names
    workflow.connect(fillna, "column_names", mergecolumnnames, "in2")

    design_unvest = pe.Node(Unvest(), name="design_unvest", run_without_submitting=True)
    workflow.connect(modelgen, "design_file", design_unvest, "in_vest")

    design_tsv = pe.Node(MergeColumns(1), name="design_tsv", run_without_submitting=True)
    workflow.connect(design_unvest, "out_no_header", design_tsv, "in1")
    workflow.connect(mergecolumnnames, "out", design_tsv, "column_names1")

    contrast_unvest = pe.Node(Unvest(), name="contrast_unvest", run_without_submitting=True)
    workflow.connect(modelgen, "con_file", contrast_unvest, "in_vest")

    contrast_tsv = pe.Node(MergeColumns(1), name="contrast_tsv", run_without_submitting=True)
    contrast_tsv.inputs.row_index = list(map(firststr, contrasts))
    workflow.connect(contrast_unvest, "out_no_header", contrast_tsv, "in1")
    workflow.connect(mergecolumnnames, "out", contrast_tsv, "column_names1")

    workflow.connect(design_tsv, "out_with_header", make_resultdicts_a, "design_matrix")
    workflow.connect(contrast_tsv, "out_with_header", make_resultdicts_a, "contrast_matrix")

    return workflow
