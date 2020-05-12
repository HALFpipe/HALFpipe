# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from ..interface import (
    InterceptOnlyModel,
    GroupModel,
    SafeMerge,
    SafeMaskMerge,
    ExtractFromResultdict,
    MakeResultdicts,
    FilterList,
    SafeMultipleRegressDesign,
    SafeFLAMEO,
    FilterResultdicts,
    AggregateResultdicts,
)

from ..utils import ravel, maplen
from ..spec import Analysis

from .memory import MemoryCalculator


def init_higherlevel_analysis_wf(analysis, memcalc=MemoryCalculator()):
    assert isinstance(analysis, Analysis)

    workflow = pe.Workflow(name=f"{analysis.name}_analysis_wf")

    inputnode = pe.Node(interface=niu.IdentityInterface(fields=["indicts"]), name="inputnode")

    indictsendpoint = (inputnode, "indicts")

    if analysis.filter is not None:
        kwargs = {}
        if analysis.spreadsheet is not None:
            kwargs["spreadsheet"] = analysis.spreadsheet
        if analysis.variables is not None:
            kwargs["variableobjs"] = analysis.variables
        filterresultsdicts = pe.Node(
            FilterResultdicts(
                filterobjs=analysis.filter, requireoneofkeys=["cope", "stat"], **kwargs
            ),
            name=f"filterresultsdicts",
        )
        workflow.connect(*indictsendpoint, filterresultsdicts, "indicts")
        indictsendpoint = (filterresultsdicts, "resultdicts")

    aggregateresultdicts = pe.Node(
        AggregateResultdicts(numinputs=1, across=analysis.across),
        name=f"aggregateresultdicts",
    )
    workflow.connect(*indictsendpoint, aggregateresultdicts, "in1")

    extractfromresultdict = pe.MapNode(
        interface=ExtractFromResultdict(
            keys=[analysis.across, "cope", "varcope", "dof_file", "mask_file"],
            aliases={"cope": ["stat"]},
        ),
        iterfield="indict",
        name="extractfromresultdict",
    )
    workflow.connect(
        [(aggregateresultdicts, extractfromresultdict, [(("resultdicts", ravel), "indict")])]
    )

    maskmerge = pe.MapNode(
        interface=SafeMaskMerge(),
        name="maskmerge",
        iterfield="in_files",
        mem_gb=memcalc.volume_std_gb * 100,
    )
    workflow.connect(extractfromresultdict, "mask_file", maskmerge, "in_files")

    copemerge = pe.MapNode(
        interface=SafeMerge(dimension="t"),
        name="copemerge",
        iterfield="in_files",
        mem_gb=memcalc.volume_std_gb * 100,
    )
    workflow.connect(extractfromresultdict, "cope", copemerge, "in_files")

    varcopemerge = pe.MapNode(
        interface=SafeMerge(dimension="t"),
        name="varcopemerge",
        iterfield="in_files",
        mem_gb=memcalc.volume_std_gb * 100,
    )
    workflow.connect(extractfromresultdict, "varcope", varcopemerge, "in_files")

    dofmerge = pe.MapNode(
        interface=SafeMerge(dimension="t"),
        name="dofmerge",
        iterfield="in_files",
        mem_gb=memcalc.volume_std_gb * 100,
    )
    workflow.connect(extractfromresultdict, "dof_file", dofmerge, "in_files")

    if analysis.type == "fixed_effects" or analysis.type == "intercept_only":
        model = pe.MapNode(
            interface=InterceptOnlyModel(),
            name="model",
            iterfield="n_copes",
            mem_gb=memcalc.min_gb,
        )
        workflow.connect([(extractfromresultdict, model, [(("cope", maplen), "n_copes")])])

        if analysis.type == "fixed_effects":
            run_mode = "fe"
        elif analysis.type == "intercept_only":
            run_mode = "flame1"

    if analysis.type == "glm":
        assert analysis.across == "subject"

        run_mode = "flame1"
        model = pe.MapNode(
            interface=GroupModel(
                spreadsheet=analysis.spreadsheet,
                contrastobjs=analysis.contrasts,
                variableobjs=analysis.variables,
            ),
            name="model",
            iterfield="subjects",
            mem_gb=memcalc.min_gb,
        )
        workflow.connect([(extractfromresultdict, model, [("subject", "subjects")])])

    multipleregressdesign = pe.MapNode(
        interface=SafeMultipleRegressDesign(),
        name="multipleregressdesign",
        iterfield=["regressors", "contrasts"],
        mem_gb=memcalc.min_gb,
    )
    workflow.connect(model, "regressors", multipleregressdesign, "regressors")
    workflow.connect(model, "contrasts", multipleregressdesign, "contrasts")

    flameo = pe.MapNode(
        interface=SafeFLAMEO(run_mode=run_mode),
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
    workflow.connect(
        [
            (maskmerge, flameo, [("merged_file", "mask_file")]),
            (copemerge, flameo, [("merged_file", "cope_file")]),
            (varcopemerge, flameo, [("merged_file", "var_cope_file")]),
            (dofmerge, flameo, [("merged_file", "dof_var_cope_file")]),
            (
                multipleregressdesign,
                flameo,
                [
                    ("design_mat", "design_file"),
                    ("design_con", "t_con_file"),
                    ("design_fts", "f_con_file"),
                    ("design_grp", "cov_split_file"),
                ],
            ),
        ]
    )

    outattrs = ["contrastname", "cope", "varcope", "zstat", "dof_file"]
    filtercons = pe.MapNode(
        interface=FilterList(fields=outattrs, pattern=r"^_"),
        iterfield=[*outattrs, "keys"],
        name="filtercons",
    )
    workflow.connect(
        [
            (
                model,
                filtercons,
                [("contrast_names", "contrastname"), ("contrast_names", "keys")],
            ),
            (
                flameo,
                filtercons,
                [
                    ("copes", "cope"),
                    ("var_copes", "varcope"),
                    ("zstats", "zstat"),
                    ("tdof", "dof_file"),
                ],
            ),
        ]
    )

    makeresultdicts = pe.MapNode(
        interface=MakeResultdicts(keys=["analysisname", *outattrs, "mask_file"]),
        iterfield=[*outattrs, "basedict", "mask_file"],
        name="makeresultdicts",
    )
    makeresultdicts.inputs.analysisname = analysis.name
    workflow.connect(maskmerge, "merged_file", makeresultdicts, "mask_file")
    workflow.connect(
        [
            (extractfromresultdict, makeresultdicts, [("remainder", "basedict")],),
            (filtercons, makeresultdicts, [(attr, attr) for attr in outattrs],),
        ]
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(fields=["resultdicts"]), name="outputnode"
    )
    workflow.connect(
        [(makeresultdicts, outputnode, [(("resultdicts", ravel), "resultdicts")])]
    )

    return workflow
