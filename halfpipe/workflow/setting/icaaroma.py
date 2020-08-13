# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from fmriprep.workflows.bold.confounds import init_ica_aroma_wf
from fmriprep.workflows.bold.resampling import init_bold_std_trans_wf
from fmriprep import config
from niworkflows.utils.spaces import Reference, SpatialReferences
from templateflow.api import get as get_template

from ...interface import (
    Exec,
    Select,
    MergeColumns,
    ApplyTransforms,
    MakeResultdicts,
    ResultdictDatasink,
    Vals,
    FilterRegressor,
)
from ...resource import get as getresource
from ...utils import firststr, loadints

from ..constants import constants
from ..memory import MemoryCalculator


spaces = SpatialReferences([Reference("MNI152NLin6Asym", {"res": "2"})])
if not spaces.is_cached():
    spaces.checkpoint()


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
    workdir=None, name="ica_aroma_components_wf", memcalc=MemoryCalculator()
):
    """

    """
    workflow = pe.Workflow(name=name)

    strfields = ["bold_file", "bold_mask", "itk_bold_to_t1", "out_warp"]
    inputnode = pe.Node(
        Exec(
            fieldtpls=[
                ("tags", None),
                ("anat2std_xfm", None),
                *[(field, "firststr") for field in strfields],
                ("bold_split", None),
                ("repetition_time", None),
                ("skip_vols", None),
                ("movpar_file", None),
                ("xforms", None),
                ("std_dseg", "ravel"),
            ]
        ),
        name="inputnode",
        run_without_submitting=True
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
        run_without_submitting=True
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    mergexfm = pe.Node(niu.Merge(numinputs=2), name="mergexfm", run_without_submitting=True)
    workflow.connect(inputnode, "anat2std_xfm", mergexfm, "in1")
    mergexfm.inputs.in2 = getresource(
        f"tpl_MNI152NLin6Asym_from_{constants.reference_space}_mode_image_xfm.h5"
    )

    compxfm = pe.Node(
        ApplyTransforms(
            dimension=3,
            print_out_composite_warp_file=True,
            output_image="ants_t1_to_mniComposite.nii.gz",
        ),
        name="compxfm",
    )
    compxfm.inputs.reference_image = firststr(
        get_template("MNI152NLin6Asym", resolution=1, suffix="T1w")
    )
    workflow.connect(mergexfm, "out", compxfm, "transforms")

    compxfmlist = pe.Node(niu.Merge(1), name="compxfmlist", run_without_submitting=True)
    workflow.connect(compxfm, "output_image", compxfmlist, "in1")

    #
    bold_std_trans_wf = init_bold_std_trans_wf(
        freesurfer=False,
        mem_gb=memcalc.series_std_gb * 0.2,  # correction factor
        omp_nthreads=config.nipype.omp_nthreads,
        spaces=spaces,
        name="bold_std_trans_wf",
        use_compression=not config.execution.low_mem,
        use_fieldwarp=True,
    )

    bold_std_trans_wf_inputnode = bold_std_trans_wf.get_node("inputnode")
    bold_std_trans_wf_inputnode.inputs.templates = ["MNI152NLin6Asym"]

    workflow.connect(compxfmlist, "out", bold_std_trans_wf, "inputnode.anat2std_xfm")
    workflow.connect(inputnode, "bold_file", bold_std_trans_wf, "inputnode.name_source")
    workflow.connect(inputnode, "bold_split", bold_std_trans_wf, "inputnode.bold_split")
    workflow.connect(inputnode, "xforms", bold_std_trans_wf, "inputnode.hmc_xforms")
    workflow.connect(inputnode, "itk_bold_to_t1", bold_std_trans_wf, "inputnode.itk_bold_to_t1")
    workflow.connect(inputnode, "bold_mask", bold_std_trans_wf, "inputnode.bold_mask")
    workflow.connect(inputnode, "out_warp", bold_std_trans_wf, "inputnode.fieldwarp")

    #
    ica_aroma_wf = init_ica_aroma_wf(
        mem_gb=memcalc.series_std_gb,
        metadata={"RepetitionTime": np.nan},
        omp_nthreads=config.nipype.omp_nthreads,
        use_fieldwarp=True,
        err_on_aroma_warn=config.workflow.aroma_err_on_warn,
        aroma_melodic_dim=config.workflow.aroma_melodic_dim,
        name="ica_aroma_wf",
    )
    ica_aroma_wf.get_node("ica_aroma").inputs.denoise_type = "no"

    add_nonsteady = ica_aroma_wf.get_node("add_nonsteady")
    ds_report_ica_aroma = ica_aroma_wf.get_node("ds_report_ica_aroma")
    ica_aroma_wf.remove_nodes([add_nonsteady, ds_report_ica_aroma])

    workflow.connect(inputnode, "repetition_time", ica_aroma_wf, "melodic.tr_sec")
    workflow.connect(inputnode, "repetition_time", ica_aroma_wf, "ica_aroma.TR")
    workflow.connect(inputnode, "movpar_file", ica_aroma_wf, "inputnode.movpar_file")
    workflow.connect(inputnode, "skip_vols", ica_aroma_wf, "inputnode.skip_vols")

    workflow.connect(bold_std_trans_wf, "outputnode.bold_std", ica_aroma_wf, "inputnode.bold_std")
    workflow.connect(
        bold_std_trans_wf, "outputnode.bold_mask_std", ica_aroma_wf, "inputnode.bold_mask_std"
    )
    workflow.connect(
        bold_std_trans_wf,
        "outputnode.spatial_reference",
        ica_aroma_wf,
        "inputnode.spatial_reference",
    )

    workflow.connect(ica_aroma_wf, "outputnode.aroma_noise_ics", outputnode, "aroma_noise_ics")
    workflow.connect(ica_aroma_wf, "outputnode.melodic_mix", outputnode, "melodic_mix")
    workflow.connect(ica_aroma_wf, "outputnode.aroma_metadata", outputnode, "aroma_metadata")
    workflow.connect(ica_aroma_wf, "ica_aroma.out_report", make_resultdicts, "ica_aroma")

    return workflow


def init_ica_aroma_regression_wf(
    name="ica_aroma_regression_wf", memcalc=MemoryCalculator(), suffix=None
):
    """

    """
    if suffix is not None:
        name = f"{name}_{suffix}"
    workflow = pe.Workflow(name=name)

    #
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["files", "vals", "mask", "melodic_mix", "aroma_metadata", "aroma_noise_ics"]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(niu.IdentityInterface(fields=["files", "mask", "vals"]), name="outputnode",)

    workflow.connect(inputnode, "mask", outputnode, "mask")

    #
    aromanoiseics = pe.Node(
        interface=niu.Function(
            input_names=["in_file"], output_names=["aroma_noise_ics"], function=loadints,
        ),
        name="aromanoiseics",
        run_without_submitting=True
    )
    workflow.connect(inputnode, "aroma_noise_ics", aromanoiseics, "in_file")

    #
    aromacolumnnames = pe.Node(
        interface=niu.Function(
            input_names=["melodic_mix", "aroma_noise_ics"], output_names=["column_names"], function=_aroma_column_names,
        ),
        name="loadaromanoiseics",
        run_without_submitting=True
    )
    workflow.connect(inputnode, "melodic_mix", aromacolumnnames, "melodic_mix")
    workflow.connect(aromanoiseics, "aroma_noise_ics", aromacolumnnames, "aroma_noise_ics")

    # add melodic_mix to the matrix
    select = pe.Node(Select(regex=r".+\.tsv"), name="select", run_without_submitting=True)
    workflow.connect(inputnode, "files", select, "in_list")

    merge_columns = pe.Node(MergeColumns(2), name="merge_columns", run_without_submitting=True)
    workflow.connect(select, "match_list", merge_columns, "in1")
    workflow.connect(inputnode, "melodic_mix", merge_columns, "in2")
    workflow.connect(aromacolumnnames, "column_names", merge_columns, "column_names2")

    merge = pe.Node(niu.Merge(2), name="merge", run_without_submitting=True)
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
    # Specifically, as both ica_aroma_components_wf and fmriprep's func_preproc_wf use
    # the bold_std_trans_wf that has the iterable node "iterablesource"
    aromavals = pe.Node(interface=Vals(), name="aromavals", mem_gb=memcalc.series_std_gb, run_without_submitting=True)
    workflow.connect(inputnode, "vals", aromavals, "vals")
    workflow.connect(inputnode, "aroma_metadata", aromavals, "aroma_metadata")
    workflow.connect(aromavals, "vals", outputnode, "vals")

    return workflow
