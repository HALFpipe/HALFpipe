# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import FrozenSet

from fmriprep import config
from nipype.interfaces import fsl
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from ... import __version__
from ...fixes import MapNode, Node
from ...interfaces.fixes.flameo import FixFLAMEO
from ...interfaces.image_maths.merge import Merge, MergeMask
from ...interfaces.result.aggregate import AggregateResultdicts
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.extract import ExtractFromResultdict
from ...interfaces.result.filter import FilterResultdicts
from ...interfaces.result.make import MakeResultdicts
from ...interfaces.stats.design import GroupDesign, InterceptOnlyDesign, MakeDesignTsv
from ...interfaces.stats.fit import ModelFit
from ...stats.algorithms import algorithms, modelfit_aliases
from ...utils.format import format_workflow
from ...utils.ops import len_for_each, ravel
from ..memory import MemoryCalculator

modelfit_model_outputs = frozenset([output for a in algorithms.values() for output in a.model_outputs])
modelfit_contrast_outputs = frozenset([output for a in algorithms.values() for output in a.contrast_outputs])
modelfit_exclude: FrozenSet[str] = frozenset([])


def _fe_run_mode(var_cope_file):
    from pathlib import Path

    if isinstance(var_cope_file, (Path, str)) and Path(var_cope_file).exists():
        return "fe"

    else:
        return "ols"


def _critical_z(voxels=None, resels=None, critical_p=0.05):
    import numpy as np
    from scipy.stats import norm  # type: ignore

    voxels = np.array(voxels)
    resels = np.array(resels)

    critical_z_array = norm.isf(critical_p / (voxels / resels))

    return critical_z_array.tolist()


def init_stats_wf(
    workdir: Path,
    model,
    numinputs=1,
    variables=None,
    memcalc: MemoryCalculator | None = None,
):
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    name = f"{format_workflow(model.name)}_wf"
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
            metadatakeys=["sources", "halfpipe_version"],
            deletekeys=["contrast"],
        ),
        name="make_resultdicts_a",
    )
    make_resultdicts_a.inputs.halfpipe_version = __version__

    statmaps = [modelfit_aliases[m] if m in modelfit_aliases else m for m in modelfit_contrast_outputs]
    make_resultdicts_b = pe.Node(
        MakeResultdicts(
            tagkeys=["model", "contrast"],
            imagekeys=statmaps,
            metadatakeys=["critical_z", "sources", "halfpipe_version"],
            missingvalues=[
                None,
                False,
            ],  # need to use False because traits doesn't support NoneType
        ),
        name="make_resultdicts_b",
    )
    make_resultdicts_b.inputs.halfpipe_version = __version__

    if model is not None:
        make_resultdicts_a.inputs.model = model.name
        make_resultdicts_b.inputs.model = model.name

    # copy out results
    merge_resultdicts_b = pe.Node(niu.Merge(3), name="merge_resultdicts_b")
    workflow.connect(make_resultdicts_a, "resultdicts", merge_resultdicts_b, "in1")
    workflow.connect(make_resultdicts_b, "resultdicts", merge_resultdicts_b, "in2")

    workflow.connect(merge_resultdicts_b, "out", outputnode, "resultdicts")

    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=str(workdir)), name="resultdict_datasink")
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
    filter_kwargs = dict(
        require_one_of_images=["effect", "reho", "falff", "alff"],
        exclude_files=[
            str(workdir / "exclude*.json"),
            str(workdir / "reports" / "exclude*.json"),
        ],
    )
    if hasattr(model, "filters") and model.filters is not None and len(model.filters) > 0:
        filter_kwargs.update(dict(filter_dicts=model.filters))
    if hasattr(model, "spreadsheet"):
        if model.spreadsheet is not None and variables is not None:
            filter_kwargs.update(dict(spreadsheet=model.spreadsheet, variable_dicts=variables))
    filter_resultdicts = pe.Node(
        interface=FilterResultdicts(**filter_kwargs),
        name="filter_resultdicts",
    )
    workflow.connect(merge_resultdicts_a, "out", filter_resultdicts, "in_dicts")

    # aggregate data structures
    # output is a list where each element represents a separate model run
    aggregate_resultdicts = pe.Node(
        AggregateResultdicts(numinputs=1, across=model.across),
        name="aggregate_resultdicts",
    )
    workflow.connect(filter_resultdicts, "resultdicts", aggregate_resultdicts, "in1")

    # extract fields from the aggregated data structure
    aliases = dict(effect=["reho", "falff", "alff"])
    extract_from_resultdict = MapNode(
        ExtractFromResultdict(keys=[model.across, *statmaps], aliases=aliases),
        iterfield="indict",
        allow_undefined_iterfield=True,
        name="extract_from_resultdict",
    )
    workflow.connect(aggregate_resultdicts, "resultdicts", extract_from_resultdict, "indict")

    # make sources metadata
    merge_sources = pe.Node(niu.Merge(3), name="merge_sources")
    workflow.connect(extract_from_resultdict, "effect", merge_sources, "in1")
    workflow.connect(extract_from_resultdict, "variance", merge_sources, "in2")
    workflow.connect(extract_from_resultdict, "mask", merge_sources, "in3")
    workflow.connect(merge_sources, "out", make_resultdicts_a, "sources")
    workflow.connect(merge_sources, "out", make_resultdicts_b, "sources")

    # copy over aggregated metadata and tags to outputs
    for make_resultdicts_node in [make_resultdicts_a, make_resultdicts_b]:
        workflow.connect(extract_from_resultdict, "tags", make_resultdicts_node, "tags")
        workflow.connect(extract_from_resultdict, "metadata", make_resultdicts_node, "metadata")
        workflow.connect(extract_from_resultdict, "vals", make_resultdicts_node, "vals")

    # create models
    if model.type in ["fe", "me"]:  # intercept only model
        countimages = pe.Node(
            niu.Function(
                input_names=["arrarr"],
                output_names="image_count",
                function=len_for_each,
            ),
            name="countimages",
        )
        workflow.connect(extract_from_resultdict, "effect", countimages, "arrarr")

        modelspec = MapNode(
            InterceptOnlyDesign(),
            name="modelspec",
            iterfield="n_copes",
            mem_gb=memcalc.min_gb,
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
        workflow.connect(extract_from_resultdict, "sub", modelspec, "subjects")

    else:
        raise ValueError()

    workflow.connect(modelspec, "contrast_names", make_resultdicts_b, "contrast")

    # run models
    if model.type in ["fe"]:  # fixed effects aggregate for multiple runs, sessions, etc.
        # pass length one inputs because we may want to use them on a higher level
        workflow.connect(
            aggregate_resultdicts,
            "non_aggregated_resultdicts",
            merge_resultdicts_b,
            "in3",
        )

        # need to merge
        mergenodeargs = {"iterfield": "in_files", "mem_gb": memcalc.volume_std_gb * 3}
        mergemask = MapNode(MergeMask(), name="mergemask", allow_undefined_iterfield=False, **mergenodeargs)
        workflow.connect(extract_from_resultdict, "mask", mergemask, "in_files")

        mergeeffect = MapNode(Merge(dimension="t"), name="mergeeffect", allow_undefined_iterfield=False, **mergenodeargs)
        workflow.connect(extract_from_resultdict, "effect", mergeeffect, "in_files")

        mergevariance = MapNode(Merge(dimension="t"), name="mergevariance", allow_undefined_iterfield=False, **mergenodeargs)
        workflow.connect(extract_from_resultdict, "variance", mergevariance, "in_files")

        fe_run_mode = MapNode(
            niu.Function(
                input_names=["var_cope_file"],
                output_names="run_mode",
                function=_fe_run_mode,
            ),
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
            FixFLAMEO(),
            name="modelfit",
            mem_gb=memcalc.volume_std_gb * 10,
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

    elif model.type in ["me", "lme"]:  # mixed effects across subjects
        # use custom implementation
        modelfit = MapNode(
            ModelFit(algorithms_to_run=model.algorithms),
            name="modelfit",
            n_procs=config.nipype.omp_nthreads,
            mem_gb=memcalc.volume_std_gb * 10,
            iterfield=[
                "mask_files",
                "cope_files",
                "var_cope_files",
                "regressors",
                "contrasts",
            ],
        )
        workflow.connect(extract_from_resultdict, "mask", modelfit, "mask_files")
        workflow.connect(extract_from_resultdict, "effect", modelfit, "cope_files")
        workflow.connect(extract_from_resultdict, "variance", modelfit, "var_cope_files")

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
                output_names="critical_z",
                function=_critical_z,
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
        name="maketsv",
    )
    workflow.connect(extract_from_resultdict, model.across, maketsv, "row_index")
    workflow.connect(modelspec, "regressors", maketsv, "regressors")
    workflow.connect(modelspec, "contrasts", maketsv, "contrasts")

    workflow.connect(maketsv, "design_tsv", make_resultdicts_a, "design_matrix")
    workflow.connect(maketsv, "contrasts_tsv", make_resultdicts_a, "contrast_matrix")

    return workflow
