# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ..interface import (
    InterceptOnlyModel,
    GroupModel,
    SafeMerge,
    SafeMaskMerge,
    ExtractFromResultdict,
    MakeResultdicts,
    FilterList,
)

from ..utils import ravel, maplen
from ..spec import Analysis

from .memory import MemoryCalculator


def init_higherlevel_analysis_wf(analysis, memcalc=MemoryCalculator()):
    assert isinstance(analysis, Analysis)

    workflow = pe.Workflow(name=analysis.name)

    inputnode = pe.Node(interface=niu.IdentityInterface(fields=["indicts"]), name="inputnode")

    extractfromresultdict = pe.MapNode(
        interface=ExtractFromResultdict(
            keys=[analysis.across, "cope", "varcope", "dof_file", "mask_file"],
            aliases={"cope": ["stat"]},
        ),
        iterfield="indict",
        name="extractfromresultdict",
    )
    workflow.connect(inputnode, "indicts", extractfromresultdict, "indict")

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
        interface=fsl.MultipleRegressDesign(),
        name="multipleregressdesign",
        iterfield=["regressors", "contrasts"],
        mem_gb=memcalc.min_gb,
    )
    workflow.connect(model, "regressors", multipleregressdesign, "regressors")
    workflow.connect(model, "contrasts", multipleregressdesign, "contrasts")

    flameo = pe.MapNode(
        interface=fsl.FLAMEO(run_mode=run_mode),
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
    workflow.connect(maskmerge, "merged_file", flameo, "mask_file")
    workflow.connect(copemerge, "merged_file", flameo, "cope_file")
    workflow.connect(varcopemerge, "merged_file", flameo, "var_cope_file")
    workflow.connect(dofmerge, "merged_file", flameo, "dof_var_cope_file")
    workflow.connect(multipleregressdesign, "design_mat", flameo, "design_file")
    workflow.connect(multipleregressdesign, "design_con", flameo, "t_con_file")
    workflow.connect(multipleregressdesign, "design_fts", flameo, "f_con_file")
    workflow.connect(multipleregressdesign, "design_grp", flameo, "cov_split_file")

    filtercons = pe.Node(
        interface=FilterList(
            fields=["contrastname", "cope", "varcope", "zstat", "dof_file"], pattern=r"^_"
        ),
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
                    (("copes", ravel), "cope"),
                    (("var_copes", ravel), "varcope"),
                    (("zstats", ravel), "zstat"),
                    (("tdof", ravel), "dof_file"),
                ],
            ),
        ]
    )

    outputnode = pe.Node(
        interface=MakeResultdicts(
            keys=[
                "analysisname",
                "contrastname",
                "cope",
                "varcope",
                "zstat",
                "dof_file",
                "mask_file",
            ]
        ),
        name="outputnode",
    )
    outputnode.inputs.analysisname = analysis.name
    workflow.connect(maskmerge, "merged_file", outputnode, "mask_file")
    workflow.connect(
        [
            (extractfromresultdict, outputnode, [("remainder", "basedict")],),
            (
                filtercons,
                outputnode,
                [
                    ("contrastname", "contrastname"),
                    ("cope", "cope"),
                    ("varcope", "varcope"),
                    ("zstat", "zstat"),
                    ("dof_file", "dof_file"),
                ],
            ),
        ]
    )

    return workflow
