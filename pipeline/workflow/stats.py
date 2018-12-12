# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pandas as pd

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

def gen_merge_op_str(files):
    out = []
    for file in files:
        with open(file) as f:
            text = f.read()
        out.append("-abs -bin -mul %f" % float(text))
    return out

def get_len(x):
    return len(x)


def init_higherlevel_wf(run_mode = "flame1", name = "higherlevel", 
        subjects = None, covariates = None,
        subject_groups = None, group_contrasts = None):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface = niu.IdentityInterface(
            fields = ["copes", "varcopes", "dof_files", "mask_files"]
        ), 
        name = "inputnode"
    )

    outputnode = pe.Node(
        interface = niu.IdentityInterface(
            fields = ["copes", "varcopes", "zstats", "dof_files", "mask_file"]
        ), 
        name = "outputnode"
    )
    
    maskmerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "maskmerge"
    )
    maskagg = pe.Node(
        interface = fsl.ImageMaths(
            op_string = "-Tmean -thr 1 -bin"
        ),
        name = "maskagg"
    )
    
    gendofimage = pe.MapNode(
        interface = fsl.ImageMaths(),
        iterfield = ["in_file", "op_string"],
        name = "gendofimage"
    )

    copemerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "copemerge"
    )

    varcopemerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "varcopemerge"
    )
    
    dofmerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "dofmerge"
    )
    
    # one-sample t-test
    contrasts = [["mean", "T", ["intercept"], [1]]]
    level2model = pe.Node(
        interface = fsl.MultipleRegressDesign(
            regressors = {"intercept": [1.0 for s in subjects]},
            contrasts = contrasts
        ),
        name = "l2model"
    )
            
    if covariates is not None:
        regressors = {k:[float(v[s]) for s in subjects] for k, v in covariates.items()}
        if subject_groups is None:
            # one-sample t-test with covariates
            regressors["intercept"] = [1.0 for s in subjects]
            level2model = pe.Node(
                interface = fsl.MultipleRegressDesign(
                    regressors = regressors,
                    contrasts = contrasts
                ),
                name = "l2model"
            )
        else: 
            # two-sample t-tests with covariates
            dummies = pd.Series(subject_groups).str.get_dummies().to_dict()
            dummies = {k:[float(v[s]) for s in subjects] for k, v in dummies.items()}
            regressors.update(dummies)
            
            contrasts = [[k, "T"] + list(map(list, zip(*v.items()))) for k, v in group_contrasts.items()]
            
            level2model = pe.Node(
                interface = fsl.MultipleRegressDesign(
                    regressors = regressors,
                    contrasts = contrasts
                ),
                name = "l2model"
            )
    
    contrast_names = [c[0] for c in contrasts]
    
    flameo = pe.MapNode(
        interface=fsl.FLAMEO(
            run_mode = run_mode
        ),
        name="flameo",
        iterfield=["cope_file", "var_cope_file"]
    )
    
    workflow.connect([
        (inputnode, copemerge, [
            ("copes", "in_files")
        ]),
        (inputnode, varcopemerge, [
            ("varcopes", "in_files")
        ]),
        
        (inputnode, maskmerge, [
            ("mask_files", "in_files")
        ]),
        (maskmerge, maskagg, [
            ("merged_file", "in_file")
        ]),
        
        (inputnode, gendofimage, [
            ("copes", "in_file"),
            (("dof_files", gen_merge_op_str), "op_string")
        ]),
        (gendofimage, dofmerge, [
            ("out_file", "in_files")
        ]),
        
        (copemerge, flameo, [
            ("merged_file", "cope_file")
        ]),
        (varcopemerge, flameo, [
            ("merged_file", "var_cope_file")
        ]),
        (dofmerge, flameo, [
            ("merged_file", "dof_var_cope_file")
        ]),
        (maskagg, flameo, [
            ("out_file", "mask_file")
        ]),
        (level2model, flameo, [
            ("design_mat", "design_file"),
            ("design_con", "t_con_file"), 
            ("design_grp", "cov_split_file")
        ]),
        
        (flameo, outputnode, [
            ("copes", "copes"),
            ("var_copes", "varcopes"), 
            ("zstats", "zstats"),
            ("tdof", "dof_files")
        ]),
        (maskagg, outputnode, [
            ("out_file", "mask_file")
        ])
    ])
    
    return workflow, contrast_names
