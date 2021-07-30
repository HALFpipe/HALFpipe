# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import FrozenSet

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from fmriprep import config

from ...interface.stats import (
    InterceptOnlyDesign,
    GroupDesign,
    ModelFit,
)
from ...interface.resultdict.datasink import ResultdictDatasink
from ...interface import (
    Merge,
    MergeMask,
    ExtractFromResultdict,
    MakeResultdicts,
    FLAMEO as FSLFLAMEO,
    FilterResultdicts,
    AggregateResultdicts,
    MakeDesignTsv,
)
from ...utils import ravel, formatlikebids, lenforeach
from ..memory import MemoryCalculator
from ...stats.algorithms import algorithms, modelfit_aliases
from ...fixes import Node, MapNode

modelfit_model_outputs = frozenset([
    output
    for a in algorithms.values()
    for output in a.model_outputs
])
modelfit_contrast_outputs = frozenset([
    output
    for a in algorithms.values()
    for output in a.contrast_outputs
])
modelfit_exclude: FrozenSet[str] = frozenset([])


def _fe_run_mode(var_cope_file):
    from pathlib import Path

    if isinstance(var_cope_file, (Path, str)) and Path(var_cope_file).exists():
        return "fe"

    else:
        return "ols"


def _critical_z(voxels=None, resels=None, critical_p=0.05):
    import numpy as np
    from scipy.stats import norm

    voxels = np.array(voxels)
    resels = np.array(resels)

    critical_z_array = norm.isf(critical_p / (voxels / resels))

    return critical_z_array.tolist()


def init_model_wf(
        workdir=None,
        numinputs=1,
        model=None,
        variables=None,
        memcalc=MemoryCalculator.default()
):
    name = f"{formatlikebids(model.name)}_wf"
    workflow = pe.Workflow(name=name)

    if model is None:
        return workflow

    #
    inputnode = Node(
        niu.IdentityInterface(fields=[f"in{i:d}" for i in range(1, numinputs + 1)]),
        allow_missing_input_source=True,
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    # setup outputs
    make_resultdicts_a = pe.Node(
        MakeResultdicts(
            tagkeys=["model", "contrast"],
            imagekeys=["design_matrix", "contrast_matrix", *modelfit_model_outputs],
            metadatakeys=["contrast_name"],
            deletekeys=["contrast"],
        ),
        name="make_resultdicts_a",
    )

    statmaps = [
        modelfit_aliases[m] if m in modelfit_aliases else m
        for m in modelfit_contrast_outputs
    ]
    make_resultdicts_b = pe.Node(
        MakeResultdicts(
            tagkeys=["model", "contrast"],
            imagekeys=statmaps,
            metadatakeys=["critical_z"],
            missingvalues=[None, False],  # need to use False because traits doesn't support NoneType
        ),
        name="make_resultdicts_b",
    )

    if model is not None:
        make_resultdicts_a.inputs.model = model.name
        make_resultdicts_b.inputs.model = model.name

    # only output statistical map (_b) result dicts because the design matrix (_a) is
    # not relevant for higher level analyses
    workflow.connect(make_resultdicts_b, "resultdicts", outputnode, "resultdicts")

    # copy out results
    merge_resultdicts_b = pe.Node(niu.Merge(2), name="merge_resultdicts_b")
    workflow.connect(make_resultdicts_a, "resultdicts", merge_resultdicts_b, "in1")
    workflow.connect(make_resultdicts_b, "resultdicts", merge_resultdicts_b, "in2")

    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(merge_resultdicts_b, "out", resultdict_datasink, "indicts")

    # merge inputs
    merge_resultdicts_a = Node(
        niu.Merge(numinputs),
        allow_missing_input_source=True,
        name="merge_resultdicts_a",
    )
    for i in range(1, numinputs + 1):
        workflow.connect(inputnode, f"in{i:d}", merge_resultdicts_a, f"in{i:d}")

    # filter inputs
    filterkwargs = dict(
        requireoneofimages=["effect", "reho", "falff", "alff"],
        excludefiles=str(Path(workdir) / "exclude*.json"),
    )
    if hasattr(model, "filters") and model.filters is not None and len(model.filters) > 0:
        filterkwargs.update(dict(filterdicts=model.filters))
    if hasattr(model, "spreadsheet"):
        if model.spreadsheet is not None and variables is not None:
            filterkwargs.update(dict(spreadsheet=model.spreadsheet, variabledicts=variables))
    filterresultdicts = pe.Node(
        interface=FilterResultdicts(**filterkwargs),
        name="filterresultdicts",
    )
    workflow.connect(merge_resultdicts_a, "out", filterresultdicts, "indicts")

    # aggregate data structures
    # output is a list where each element respresents a separate model run
    aggregateresultdicts = pe.Node(
        AggregateResultdicts(numinputs=1, across=model.across), name="aggregateresultdicts"
    )
    workflow.connect(filterresultdicts, "resultdicts", aggregateresultdicts, "in1")

    # extract fields from the aggregated data structure
    aliases = dict(effect=["reho", "falff", "alff"])
    extractfromresultdict = MapNode(
        ExtractFromResultdict(keys=[model.across, *statmaps], aliases=aliases),
        iterfield="indict",
        allow_undefined_iterfield=True,
        name="extractfromresultdict",
    )
    workflow.connect(aggregateresultdicts, "resultdicts", extractfromresultdict, "indict")

    # copy over aggregated metadata and tags to outputs
    for make_resultdicts_node in [make_resultdicts_a, make_resultdicts_b]:
        workflow.connect(extractfromresultdict, "tags", make_resultdicts_node, "tags")
        workflow.connect(extractfromresultdict, "metadata", make_resultdicts_node, "metadata")
        workflow.connect(extractfromresultdict, "vals", make_resultdicts_node, "vals")

    # create models
    if model.type in ["fe", "me"]:  # intercept only model
        countimages = pe.Node(
            niu.Function(input_names=["arrarr"], output_names=["image_count"], function=lenforeach),
            name="countimages",
        )
        workflow.connect(extractfromresultdict, "effect", countimages, "arrarr")

        modelspec = MapNode(
            InterceptOnlyDesign(), name="modelspec", iterfield="n_copes", mem_gb=memcalc.min_gb
        )
        workflow.connect(countimages, "image_count", modelspec, "n_copes")

    elif model.type in ["lme"]:  # glm
        modelspec = MapNode(
            GroupDesign(
                spreadsheet=model.spreadsheet,
                contrastdicts=model.contrasts,
                variabledicts=variables,
            ),
            name="modelspec",
            iterfield="subjects",
            mem_gb=memcalc.min_gb,
        )
        workflow.connect(extractfromresultdict, "sub", modelspec, "subjects")

    else:
        raise ValueError()

    workflow.connect(modelspec, "contrast_numbers", make_resultdicts_b, "contrast")
    workflow.connect(modelspec, "contrast_names", make_resultdicts_b, "contrast_name")

    # run models
    if model.type in ["fe"]:

        # need to merge
        mergenodeargs = dict(iterfield="in_files", mem_gb=memcalc.volume_std_gb * numinputs)
        mergemask = MapNode(MergeMask(), name="mergemask", **mergenodeargs)
        workflow.connect(extractfromresultdict, "mask", mergemask, "in_files")

        mergeeffect = MapNode(Merge(dimension="t"), name="mergeeffect", **mergenodeargs)
        workflow.connect(extractfromresultdict, "effect", mergeeffect, "in_files")

        mergevariance = MapNode(Merge(dimension="t"), name="mergevariance", **mergenodeargs)
        workflow.connect(extractfromresultdict, "variance", mergevariance, "in_files")

        fe_run_mode = MapNode(
            niu.Function(input_names=["var_cope_file"], output_names=["run_mode"], function=_fe_run_mode),
            iterfield=["var_cope_file"],
            name="fe_run_mode",
        )
        workflow.connect(mergevariance, "merged_file", fe_run_mode, "var_cope_file")

        # prepare design matrix
        multipleregressdesign = MapNode(
            fsl.MultipleRegressDesign(),
            name="multipleregressdesign",
            iterfield=["regressors", "contrasts"],
            mem_gb=memcalc.min_gb,
        )
        workflow.connect(modelspec, "regressors", multipleregressdesign, "regressors")
        workflow.connect(modelspec, "contrasts", multipleregressdesign, "contrasts")

        # use FSL implementation
        modelfit = MapNode(
            FSLFLAMEO(),
            name="modelfit",
            mem_gb=memcalc.volume_std_gb * 100,
            iterfield=[
                "run_mode",
                "mask_file",
                "cope_file",
                "var_cope_file",
                "design_file",
                "t_con_file",
                "cov_split_file",
            ],
        )
        workflow.connect(fe_run_mode, "run_mode", modelfit, "run_mode")
        workflow.connect(mergemask, "merged_file", modelfit, "mask_file")
        workflow.connect(mergeeffect, "merged_file", modelfit, "cope_file")
        workflow.connect(mergevariance, "merged_file", modelfit, "var_cope_file")
        workflow.connect(multipleregressdesign, "design_mat", modelfit, "design_file")
        workflow.connect(multipleregressdesign, "design_con", modelfit, "t_con_file")
        workflow.connect(multipleregressdesign, "design_grp", modelfit, "cov_split_file")

        # mask output
        workflow.connect(mergemask, "merged_file", make_resultdicts_b, "mask")

    elif model.type in ["me", "lme"]:

        # use custom implementation
        modelfit = MapNode(
            ModelFit(algorithms_to_run=model.algorithms),
            name="modelfit",
            n_procs=config.nipype.omp_nthreads,
            mem_gb=memcalc.volume_std_gb * 100,
            iterfield=[
                "mask_files",
                "cope_files",
                "var_cope_files",
                "regressors",
                "contrasts",
            ],
        )
        workflow.connect(extractfromresultdict, "mask", modelfit, "mask_files")
        workflow.connect(extractfromresultdict, "effect", modelfit, "cope_files")
        workflow.connect(extractfromresultdict, "variance", modelfit, "var_cope_files")

        workflow.connect(modelspec, "regressors", modelfit, "regressors")
        workflow.connect(modelspec, "contrasts", modelfit, "contrasts")

        # random field theory
        smoothest = MapNode(
            fsl.SmoothEstimate(),
            iterfield=["zstat_file", "mask_file"],
            name="smoothest",
            allow_undefined_iterfield=True,
        )
        workflow.connect([(modelfit, smoothest, [(("zstats", ravel), "zstat_file")])])
        workflow.connect([(modelfit, smoothest, [(("masks", ravel), "mask_file")])])

        criticalz = pe.Node(
            niu.Function(
                input_names=["voxels", "resels"],
                output_names=["critical_z"],
                function=_critical_z
            ),
            name="criticalz",
        )
        workflow.connect(smoothest, "volume", criticalz, "voxels")
        workflow.connect(smoothest, "resels", criticalz, "resels")
        workflow.connect(criticalz, "critical_z", make_resultdicts_b, "critical_z")

    else:
        raise ValueError()

    # connect modelfit outputs
    assert modelfit.outputs is not None
    for k, _ in modelfit.outputs.items():
        if k in modelfit_exclude:
            continue

        attr = k
        if k in modelfit_aliases:
            attr = modelfit_aliases[k]
        if attr in statmaps:
            workflow.connect(modelfit, k, make_resultdicts_b, attr)
        else:
            workflow.connect(modelfit, k, make_resultdicts_a, attr)

    # make tsv files for design and contrast matrices
    maketsv = MapNode(
        MakeDesignTsv(),
        iterfield=["regressors", "contrasts", "row_index"],
        name="maketsv"
    )
    workflow.connect(extractfromresultdict, model.across, maketsv, "row_index")
    workflow.connect(modelspec, "regressors", maketsv, "regressors")
    workflow.connect(modelspec, "contrasts", maketsv, "contrasts")

    workflow.connect(maketsv, "design_tsv", make_resultdicts_a, "design_matrix")
    workflow.connect(maketsv, "contrasts_tsv", make_resultdicts_a, "contrast_matrix")

    return workflow
