# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from ...interface import (
    InterceptOnlyModel,
    LinearModel,
    Merge,
    MergeMask,
    ExtractFromResultdict,
    MakeResultdicts,
    FilterList,
    MultipleRegressDesign,
    FLAMEO,
    FilterResultdicts,
    AggregateResultdicts,
    ResultdictDatasink,
    MergeColumns
)

from ...utils import ravel, formatlikebids, lenforeach

from ..memory import MemoryCalculator


def init_model_wf(workdir=None, numinputs=1, model=None, variables=None, memcalc=MemoryCalculator()):
    name = f"{formatlikebids(model.name)}_wf"
    workflow = pe.Workflow(name=name)

    if model is None:
        return workflow

    #
    inputnode = pe.Node(
        niu.IdentityInterface(fields=[f"in{i:d}" for i in range(1, numinputs + 1)]),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    #
    statmaps = ["effect", "variance", "z", "dof", "mask"]
    make_resultdicts_a = pe.Node(
        MakeResultdicts(tagkeys=["model"], imagekeys=["design_matrix", "contrast_matrix"]),
        name="make_resultdicts_a",
        run_without_submitting=True
    )
    if model is not None:
        make_resultdicts_a.inputs.model = model.name
    make_resultdicts_b = pe.Node(
        MakeResultdicts(
            tagkeys=["model", "contrast"],
            imagekeys=statmaps
        ),
        name="make_resultdicts_b",
        run_without_submitting=True
    )
    if model is not None:
        make_resultdicts_b.inputs.model = model.name

    workflow.connect(make_resultdicts_b, "resultdicts", outputnode, "resultdicts")

    #
    merge_resultdicts_b = pe.Node(niu.Merge(2), name="merge_resultdicts_b")
    workflow.connect(make_resultdicts_a, "resultdicts", merge_resultdicts_b, "in1")
    workflow.connect(make_resultdicts_b, "resultdicts", merge_resultdicts_b, "in2")
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(merge_resultdicts_b, "out", resultdict_datasink, "indicts")

    #
    merge_resultdicts_a = pe.Node(niu.Merge(numinputs), name="merge_resultdicts_a", run_without_submitting=True)
    for i in range(1, numinputs + 1):
        workflow.connect(inputnode, f"in{i:d}", merge_resultdicts_a, f"in{i:d}")

    #
    aggregateresultdicts = pe.Node(
        AggregateResultdicts(numinputs=1, across=model.across), name=f"aggregateresultdicts", run_without_submitting=True
    )

    #
    if hasattr(model, "filters") and model.filters is not None and len(model.filters) > 0:
        kwargs = dict(filterdicts=model.filters, requireoneofimages=["effect", "reho", "falff", "alff"])
        if hasattr(model, "spreadsheet"):
            if model.spreadsheet is not None and variables is not None:
                kwargs.update(dict(spreadsheet=model.spreadsheet, variableobjs=variables))
        filterresultsdicts = pe.Node(FilterResultdicts(**kwargs), name="filterresultsdicts", run_without_submitting=True)
        workflow.connect(merge_resultdicts_a, "out", filterresultsdicts, "indicts")
        workflow.connect(filterresultsdicts, "resultdicts", aggregateresultdicts, "in1")
    else:
        workflow.connect(merge_resultdicts_a, "out", aggregateresultdicts, "in1")

    #
    ravelresultdicts = pe.Node(
        niu.Function(input_names=["obj"], output_names=["out_list"], function=ravel),
        name="ravelresultdicts",
        run_without_submitting=True
    )
    workflow.connect(aggregateresultdicts, "resultdicts", ravelresultdicts, "obj")

    #
    aliases = dict(effect=["reho", "falff", "alff"])
    extractfromresultdict = pe.MapNode(
        ExtractFromResultdict(keys=[model.across, *statmaps], aliases=aliases),
        iterfield="indict",
        name="extractfromresultdict",
        run_without_submitting=True
    )
    workflow.connect(ravelresultdicts, "out_list", extractfromresultdict, "indict")

    workflow.connect(extractfromresultdict, "tags", make_resultdicts_a, "tags")
    workflow.connect(extractfromresultdict, "metadata", make_resultdicts_a, "metadata")
    workflow.connect(extractfromresultdict, "tags", make_resultdicts_b, "tags")
    workflow.connect(extractfromresultdict, "metadata", make_resultdicts_b, "metadata")

    #
    mergenodeargs = dict(iterfield="in_files", mem_gb=memcalc.volume_std_gb * numinputs)
    mergemask = pe.MapNode(MergeMask(), name="mergemask", **mergenodeargs)
    workflow.connect(extractfromresultdict, "mask", mergemask, "in_files")

    mergeeffect = pe.MapNode(Merge(dimension="t"), name="mergeeffect", **mergenodeargs)
    workflow.connect(extractfromresultdict, "effect", mergeeffect, "in_files")

    mergevariance = pe.MapNode(Merge(dimension="t"), name="mergevariance", **mergenodeargs)
    workflow.connect(extractfromresultdict, "variance", mergevariance, "in_files")

    mergedof = pe.MapNode(Merge(dimension="t"), name="mergedof", **mergenodeargs)
    workflow.connect(extractfromresultdict, "dof", mergedof, "in_files")

    # create models
    if model.type in ["fe", "me"]:  # intercept only model
        run_mode = dict(fe="fe", me="flame1")[model.type]

        countimages = pe.MapNode(
            niu.Function(input_names=["arrarr"], output_names=["image_count"], function=lenforeach),
            iterfield="arrarr",
            name="countimages",
            run_without_submitting=True
        )
        workflow.connect(extractfromresultdict, "effect", countimages, "arrarr")

        modelspec = pe.MapNode(
            InterceptOnlyModel(), name="modelspec", iterfield="n_copes", mem_gb=memcalc.min_gb, run_without_submitting=True
        )
        workflow.connect(countimages, "image_count", modelspec, "n_copes")

    elif model.type in ["lme"]:  # glm
        run_mode = "flame1"

        modelspec = pe.MapNode(
            LinearModel(
                spreadsheet=model.spreadsheet,
                contrastobjs=model.contrasts,
                variableobjs=variables,
            ),
            name="modelspec",
            iterfield="subjects",
            mem_gb=memcalc.min_gb,
            run_without_submitting=True
        )
        workflow.connect(extractfromresultdict, "subject", modelspec, "subjects")

    # prepare design matrix
    multipleregressdesign = pe.MapNode(
        MultipleRegressDesign(),
        name="multipleregressdesign",
        iterfield=["regressors", "contrasts"],
        mem_gb=memcalc.min_gb,
    )
    workflow.connect(modelspec, "regressors", multipleregressdesign, "regressors")
    workflow.connect(modelspec, "contrasts", multipleregressdesign, "contrasts")

    #
    flameo = pe.MapNode(
        FLAMEO(run_mode=run_mode),
        name="flameo",
        mem_gb=memcalc.volume_std_gb * 100,
        iterfield=[
            "mask_file",
            "cope_file",
            "var_cope_file",
            "dof_var_cope_file",
            "design_file",
            "t_con_file",
            "f_con_file",
            "cov_split_file",
        ],
    )
    workflow.connect(mergemask, "merged_file", flameo, "mask_file")
    workflow.connect(mergeeffect, "merged_file", flameo, "cope_file")
    workflow.connect(mergevariance, "merged_file", flameo, "var_cope_file")
    workflow.connect(mergedof, "merged_file", flameo, "dof_var_cope_file")
    workflow.connect(multipleregressdesign, "design_mat", flameo, "design_file")
    workflow.connect(multipleregressdesign, "design_con", flameo, "t_con_file")
    workflow.connect(multipleregressdesign, "design_fts", flameo, "f_con_file")
    workflow.connect(multipleregressdesign, "design_grp", flameo, "cov_split_file")

    #
    filtercons = pe.MapNode(
        FilterList(fields=["contrast_names", *statmaps], pattern=r"^_"),
        iterfield=["keys", "contrast_names", *statmaps],
        name="filtercons",
        run_without_submitting=True
    )
    workflow.connect(modelspec, "contrast_names", filtercons, "keys")
    workflow.connect(modelspec, "contrast_names", filtercons, "contrast_names")
    workflow.connect(mergemask, "merged_file", filtercons, "mask")
    workflow.connect(flameo, "copes", filtercons, "effect")
    workflow.connect(flameo, "var_copes", filtercons, "varcope")
    workflow.connect(flameo, "zstats", filtercons, "z")
    workflow.connect(flameo, "tdof", filtercons, "dof")

    #
    workflow.connect(filtercons, "contrast_names", make_resultdicts_b, "contrast")
    for s in statmaps:
        workflow.connect(filtercons, s, make_resultdicts_b, s)

    #
    design_tsv = pe.MapNode(MergeColumns(1), iterfield=["row_index", "in1", "column_names1"], name="design_tsv", run_without_submitting=True)
    workflow.connect(extractfromresultdict, model.across, design_tsv, "row_index")
    workflow.connect(multipleregressdesign, "design_mat", design_tsv, "in1")
    workflow.connect(multipleregressdesign, "regs", design_tsv, "column_names1")

    contrast_tsv = pe.Node(MergeColumns(1), iterfield=["in1", "column_names1", "row_index"], name="contrast_tsv", run_without_submitting=True)
    workflow.connect(modelspec, "contrast_names", contrast_tsv, "row_index")
    workflow.connect(multipleregressdesign, "design_con", contrast_tsv, "in1")
    workflow.connect(multipleregressdesign, "regs", contrast_tsv, "column_names1")

    workflow.connect(design_tsv, "out_with_header", make_resultdicts_a, "design_matrix")
    workflow.connect(contrast_tsv, "out_with_header", make_resultdicts_a, "contrast_matrix")

    return workflow
