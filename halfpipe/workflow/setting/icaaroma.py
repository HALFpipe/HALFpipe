# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import nan

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from fmriprep.workflows.bold.confounds import init_ica_aroma_wf
from fmriprep import config

from ...interface import (
    Select,
    MergeColumns,
    MakeResultdicts,
    ResultdictDatasink,
    FilterRegressor,
)
from ...interface.report.vals import UpdateVals
from ...utils import loadints

from ..memory import MemoryCalculator


def _aroma_column_names(melodic_mix=None, aroma_noise_ics=None):
    import numpy as np
    from halfpipe.utils import ncol

    ncomponents = ncol(melodic_mix)
    leading_zeros = int(np.ceil(np.log10(ncomponents)))
    column_names = []
    for i in range(1, ncomponents + 1):
        if i in aroma_noise_ics:
            column_names.append(f"aroma_noise_{i:0{leading_zeros}d}")
        else:
            column_names.append(f"aroma_signal_{i:0{leading_zeros}d}")

    return column_names


def init_ica_aroma_components_wf(
    workdir=None, name="ica_aroma_components_wf", memcalc=MemoryCalculator.default()
):
    """

    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=[
            "alt_bold_std",
            "alt_bold_mask_std",
            "alt_spatial_reference",
            "tags",
            "skip_vols",
            "repetition_time",
            "movpar_file",
        ]),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["aroma_noise_ics", "melodic_mix", "aroma_metadata", "aromavals"]
        ),
        name="outputnode",
    )

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(reportkeys=["ica_aroma"]),
        name="make_resultdicts",
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    ica_aroma_wf = init_ica_aroma_wf(
        mem_gb=memcalc.series_std_gb,
        metadata={"RepetitionTime": nan},
        omp_nthreads=config.nipype.omp_nthreads,
        err_on_aroma_warn=config.workflow.aroma_err_on_warn,
        aroma_melodic_dim=config.workflow.aroma_melodic_dim,
        name="ica_aroma_wf",
    )

    ica_aroma_node = ica_aroma_wf.get_node("ica_aroma")
    assert isinstance(ica_aroma_node, pe.Node)
    ica_aroma_node.inputs.denoise_type = "no"

    add_nonsteady = ica_aroma_wf.get_node("add_nonsteady")
    ds_report_ica_aroma = ica_aroma_wf.get_node("ds_report_ica_aroma")
    ica_aroma_wf.remove_nodes([add_nonsteady, ds_report_ica_aroma])

    workflow.connect(inputnode, "repetition_time", ica_aroma_wf, "melodic.tr_sec")
    workflow.connect(inputnode, "repetition_time", ica_aroma_wf, "ica_aroma.TR")
    workflow.connect(inputnode, "movpar_file", ica_aroma_wf, "inputnode.movpar_file")
    workflow.connect(inputnode, "skip_vols", ica_aroma_wf, "inputnode.skip_vols")

    workflow.connect(inputnode, "alt_bold_std", ica_aroma_wf, "inputnode.bold_std")
    workflow.connect(inputnode, "alt_bold_mask_std", ica_aroma_wf, "inputnode.bold_mask_std")
    workflow.connect(inputnode, "alt_spatial_reference", ica_aroma_wf, "inputnode.spatial_reference")

    workflow.connect(ica_aroma_wf, "outputnode.aroma_noise_ics", outputnode, "aroma_noise_ics")
    workflow.connect(ica_aroma_wf, "outputnode.melodic_mix", outputnode, "melodic_mix")
    workflow.connect(ica_aroma_wf, "outputnode.aroma_metadata", outputnode, "aroma_metadata")
    workflow.connect(ica_aroma_wf, "ica_aroma.out_report", make_resultdicts, "ica_aroma")

    return workflow


def init_ica_aroma_regression_wf(
    workdir=None, name="ica_aroma_regression_wf", memcalc=MemoryCalculator.default(), suffix=None
):
    """

    """
    if suffix is not None:
        name = f"{name}_{suffix}"
    workflow = pe.Workflow(name=name)

    #
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["files", "mask", "tags", "vals", "melodic_mix", "aroma_metadata", "aroma_noise_ics"]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["files", "mask", "vals"]), name="outputnode",)

    workflow.connect(inputnode, "mask", outputnode, "mask")

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(),
        name="make_resultdicts",
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    aromanoiseics = pe.Node(
        interface=niu.Function(
            input_names=["in_file"], output_names=["aroma_noise_ics"], function=loadints,
        ),
        name="aromanoiseics",
    )
    workflow.connect(inputnode, "aroma_noise_ics", aromanoiseics, "in_file")

    #
    aromacolumnnames = pe.Node(
        interface=niu.Function(
            input_names=["melodic_mix", "aroma_noise_ics"], output_names=["column_names"], function=_aroma_column_names,
        ),
        name="loadaromanoiseics",
    )
    workflow.connect(inputnode, "melodic_mix", aromacolumnnames, "melodic_mix")
    workflow.connect(aromanoiseics, "aroma_noise_ics", aromacolumnnames, "aroma_noise_ics")

    # add melodic_mix to the matrix
    select = pe.Node(Select(regex=r".+\.tsv"), name="select")
    workflow.connect(inputnode, "files", select, "in_list")

    merge_columns = pe.Node(MergeColumns(2), name="merge_columns")
    workflow.connect(select, "match_list", merge_columns, "in1")
    workflow.connect(inputnode, "melodic_mix", merge_columns, "in2")
    workflow.connect(aromacolumnnames, "column_names", merge_columns, "column_names2")

    merge = pe.Node(niu.Merge(2), name="merge")
    workflow.connect(select, "other_list", merge, "in1")
    workflow.connect(merge_columns, "out_with_header", merge, "in2")

    #
    filter_regressor = pe.MapNode(
        FilterRegressor(mask=False),
        iterfield="in_file",
        name="filter_regressor",
        mem_gb=memcalc.series_std_gb,
    )

    workflow.connect(merge, "out", filter_regressor, "in_file")
    workflow.connect(inputnode, "mask", filter_regressor, "mask")
    workflow.connect(inputnode, "melodic_mix", filter_regressor, "design_file")
    workflow.connect(aromanoiseics, "aroma_noise_ics", filter_regressor, "filter_columns")

    workflow.connect(filter_regressor, "out_file", outputnode, "files")

    # We cannot do this in the ica_aroma_components_wf, as having two iterable node
    # with the same name downstream from each other leads nipype to consider them equal
    # even if a joinnode is inbetween
    # Specifically, both ica_aroma_components_wf and fmriprep's func_preproc_wf use
    # the bold_std_trans_wf that has the iterable node "iterablesource"
    # This way there is no dependency
    aromavals = pe.Node(interface=UpdateVals(), name="aromavals", mem_gb=memcalc.volume_std_gb)
    workflow.connect(inputnode, "vals", aromavals, "vals")
    workflow.connect(inputnode, "aroma_metadata", aromavals, "aroma_metadata")

    workflow.connect(aromavals, "vals", outputnode, "vals")
    workflow.connect(aromavals, "vals", make_resultdicts, "vals")

    return workflow
