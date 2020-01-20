# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pandas as pd
import numpy as np

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ..utils import flatten
from .qualitycheck import get_qualitycheck_exclude

import json

def gen_merge_op_str(files):
    """
    generate string argument to FSLMATHS that creates a dof image
    file from a dof text file

    :param files: dof text file

    """
    out = []
    for file in files:
        with open(file) as f:
            text = f.read()
        out.append("-abs -bin -mul %f" % float(text))
    return out


def get_len(x):
    """
    wrapper around len

    :param x: x

    """
    return len(x)


def init_higherlevel_wf(run_mode="flame1", name="higherlevel",
                        subjects=None, covariates=None,
                        subject_groups=None, group_contrasts=None,
                        outname=None, workdir=None, task=None): # FIXME split this into two functions
    """

    :param run_mode: mode argument passed to FSL FLAMEO (Default value = "flame1")
    :param name: workflow name (Default value = "higherlevel")
    :param subjects: list of subject names (Default value = None)
    :param covariates: two-level dictionary of covariates by name and subject (Default value = None)
    :param subject_groups: dictionary of subjects by group (Default value = None)
    :param group_contrasts: two-level dictionary of contrasts by contrast name and values by group (Default = None)
    :param outname: names of inputs for higherlevel workflow, names of outputs from firstlevel workflow
    :param workdir: the working directory to check for qualitycheck excludes
    :param task: name of task to filter excludes FIXME this shouldn"t be necessary, go by filename instead

    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["copes", "varcopes", "dof_files", "mask_files", "zstats"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["copes", "varcopes", "zstats", "dof_files", "mask_file"]
        ),
        name="outputnode"
    )

    # merge all input nii image files to one big nii file
    maskmerge = pe.Node(
        interface=fsl.Merge(dimension="t"),
        name="maskmerge"
    )
    # calculate the intersection of all masks
    maskagg = pe.Node(
        interface=fsl.ImageMaths(
            op_string="-Tmin -thr 1 -bin"
        ),
        name="maskagg"
    )

    # merge all input nii image files to one big nii file
    copemerge = pe.Node(
        interface=fsl.Merge(dimension="t"),
        name="copemerge"
    )

    # we get a text dof_file, but need to transform it to an nii image
    gendofimage = pe.MapNode(
        interface=fsl.ImageMaths(),
        iterfield=["in_file", "op_string"],
        name="gendofimage"
    )

    # merge all input nii image files to one big nii file
    varcopemerge = pe.Node(
        interface=fsl.Merge(dimension="t"),
        name="varcopemerge"
    )

    # merge all generated nii image files to one big nii file
    dofmerge = pe.Node(
        interface=fsl.Merge(dimension="t"),
        name="dofmerge"
    )

    # merge all zstat files (reho/alff/falff)
    zstatmerge = pe.Node(
        interface=fsl.Merge(dimension="t"),
        name="zstatmerge"
    )

    contrasts = [["mean", "T", ["intercept"], [1]]]

    # specify statistical analysis
    if not subjects or not covariates: # option 1: one-sample t-test
        level2model = pe.Node(
            interface = fsl.L2Model(), 
            name = "l2model"
        )
        
        workflow.connect([
            (inputnode, level2model, [
                (("copes", get_len), "num_copes")
            ]),
        ])
    elif covariates:
        # Transform covariates dict to pandas dataframe
        df_covariates = pd.DataFrame(covariates)
        
        # only keep subjects that are in this analysis
        df_covariates = df_covariates.filter(subjects)
        

            for excluded_subject in excluded_subjects:
                subject_groups.pop(excluded_subject, None)
                
        # replace not available values by numpy NaN to be ignored for demeaning
        df_covariates = df_covariates.replace({"NaN": np.nan, "n/a": np.nan, "NA": np.nan})

        for covariate in df_covariates:
            # Demean covariates for flameo
            df_covariates[covariate] = df_covariates[covariate] - df_covariates[covariate].mean()
        
        # replace np.nan by 0 for demeaned_covariates file and regression models
        df_covariates = df_covariates.replace({np.nan: 0})

        # add SubjectGroups and ID to header
        df_subject_group = pd.DataFrame.from_dict(subject_groups, orient = "index", columns = ["SubjectGroup"])
        df_covariates_forsaving = pd.concat([df_subject_group, df_covariates], axis = 1, sort = True)
        df_covariates_forsaving = df_covariates.reset_index()  # add id column
        df_covariates_forsaving = df_covariates.rename(columns = {"index": "Subject_ID"})  # rename subject column
        # save demeaned covariates to csv
        df_covariates_forsaving.to_csv(workdir + "/demeaned_covariates.csv", index = False)

        # transform into dict to extract regressors for level2model
        covariates = df_covariates.to_dict()
        
        # transform to dictionary of lists
        regressors = {k: [float(v[s]) for s in subjects] for k, v in covariates.items()}
        
        if (subject_groups is None) or (bool(subject_groups) is False):
            # one-sample t-test with covariates
            regressors["intercept"] = [1.0 for s in subjects]
            level2model = pe.Node(
                interface=fsl.MultipleRegressDesign(
                    regressors=regressors,
                    contrasts=contrasts
                ),
                name="l2model"
            )
        else:
            # two-sample t-tests with covariates

            # dummy coding of variables: group names --> numbers in the matrix
            # see fsl feat documentation
            # https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FEAT/UserGuide#Tripled_Two-Group_Difference_.28.22Tripled.22_T-Test.29
            dummies = pd.Series(subject_groups).str.get_dummies().to_dict()
            # transform to dictionary of lists
            dummies = {k: [float(v[s]) for s in subjects] for k, v in dummies.items()}
            regressors.update(dummies)

            # transform to dictionary of lists
            contrasts = [[k, "T"] + list(map(list, zip(*v.items()))) for k, v in group_contrasts.items()]

            level2model = pe.Node(
                interface=fsl.MultipleRegressDesign(
                    regressors=regressors,
                    contrasts=contrasts
                ),
                name="l2model"
            )

    contrast_names = [c[0] for c in contrasts]

    # actually run FSL FLAME

    if outname in ["reho", "alff", "falff"]:
        flameo = pe.MapNode(
            interface=fsl.FLAMEO(
                run_mode=run_mode
            ),
            name="flameo",
            iterfield=["cope_file"]  # cope_file is here z_stat file
        )
    else:
        flameo = pe.MapNode(
            interface=fsl.FLAMEO(
                run_mode=run_mode
            ),
            name="flameo",
            iterfield=["cope_file", "var_cope_file"]
        )

    # construct workflow

    if outname in ["reho", "alff", "falff"]: # FIXME no hard coded names
        workflow.connect([
            (inputnode, copemerge, [
                ("copes", "in_files")
            ]),
            (inputnode, zstatmerge, [
                ("zstats", "in_files") # FIXME alff zstats are not zstats in the flame sense, but just normalized across the volume. which zstats are thus used here?
            ]),

            (inputnode, maskmerge, [
                ("mask_files", "in_files")
            ]),
            (maskmerge, maskagg, [
                ("merged_file", "in_file")
            ]),
        ])

        workflow.connect([
            (zstatmerge, flameo, [
                ("merged_file", "cope_file")
            ])
        ])

        workflow.connect(([
            (level2model, flameo, [
                ("design_mat", "design_file"),
                ("design_con", "t_con_file"),
                ("design_grp", "cov_split_file")
            ]),

            (flameo, outputnode, [
                (("copes", flatten), "copes"),
                (("var_copes", flatten), "varcopes"),
                (("zstats", flatten), "zstats"),
                (("tdof", flatten), "dof_files")
            ]),
            (maskagg, flameo, [
                ("out_file", "mask_file")
            ]),
            (maskagg, outputnode, [
                ("out_file", "mask_file")
            ]),
        ]))
    else:
        workflow.connect([
            (inputnode, copemerge, [
                ("copes", "in_files")
            ]),

            (inputnode, maskmerge, [
                ("mask_files", "in_files")
            ]),
            (maskmerge, maskagg, [
                ("merged_file", "in_file")
            ]),
        ])

        workflow.connect([
            (inputnode, gendofimage, [
                ("copes", "in_file"),
                (("dof_files", gen_merge_op_str), "op_string")
            ]),

            (inputnode, varcopemerge, [
                ("varcopes", "in_files")
            ]),

            (gendofimage, dofmerge, [
                ("out_file", "in_files")
            ])
        ])

        workflow.connect([
            (copemerge, flameo, [
                ("merged_file", "cope_file")
            ])
        ])

        workflow.connect([
            (varcopemerge, flameo, [
                ("merged_file", "var_cope_file")
            ]),
            (dofmerge, flameo, [
                ("merged_file", "dof_var_cope_file")
            ])
        ])

        workflow.connect([
            (level2model, flameo, [
                ("design_mat", "design_file"),
                ("design_con", "t_con_file"),
                ("design_grp", "cov_split_file")
            ]),

            (flameo, outputnode, [
                (("copes", flatten), "copes"),
                (("var_copes", flatten), "varcopes"),
                (("zstats", flatten), "zstats"),
                (("tdof", flatten), "dof_files")
            ]),
            (maskagg, flameo, [
                ("out_file", "mask_file")
            ]),
            (maskagg, outputnode, [
                ("out_file", "mask_file")
            ]),
        ])
    
    return workflow, contrast_names
