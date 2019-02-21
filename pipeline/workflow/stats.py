# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pandas as pd

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
                        outname=None, workdir=None, task=None):
    """

    :param run_mode: mode argument passed to FSL FLAMEO (Default value = "flame1")
    :param name: workflow name (Default value = "higherlevel")
    :param subjects: list of subject names (Default value = None)
    :param covariates: two-level dictionary of covariates by name and subject (Default value = None)
    :param subject_groups: dictionary of subjects by group (Default value = None)
    :param group_contrasts: two-level dictionary of contrasts by contrast name and values by group (Default = None)
    :param outname: names of inputs for higherlevel workflow, names of outputs from firstlevel workflow

    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["imgs", "varcopes", "dof_files", "mask_files"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["imgs", "varcopes", "zstats", "dof_files", "mask_file"]
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
    imgmerge = pe.Node(
        interface=fsl.Merge(dimension="t"),
        name="imgmerge"
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

    # specify statistical analysis

    # Read qcresults.json and exclude bad subjects from statistics
    excluded_overview = get_qualitycheck_exclude(workdir)
    excluded_subjects = []
    if excluded_overview:
        df_exclude = pd.DataFrame(excluded_overview).transpose()
        excluded_subjects = df_exclude.loc[df_exclude[task] == True].index
        trimmed_subjects = list(subjects)
        for excluded_subject in excluded_subjects:
            trimmed_subjects.remove(excluded_subject)

        # save json file in workdir with list for included subjects if subjects were excluded due to qualitycheck
        # use of sets here for easy substraction of subjects
        included_subjects = list(set(subjects) - set(excluded_subjects))
        df_included_subjects = pd.DataFrame(included_subjects, columns=['Subjects'])
        df_included_subjects = df_included_subjects.sort_values(by=['Subjects'])  # sort by name
        df_included_subjects = df_included_subjects.reset_index(drop=True)  # reindex for ascending numbers
        json_path = workdir + '/included_subjects.json'
        df_included_subjects.to_json(json_path)
        with open(json_path, 'w') as json_file:
            # json is loaded from pandas to json and then dumped to get indent in file
            json.dump(json.loads(df_included_subjects.to_json()), json_file, indent=4)
    else:
        trimmed_subjects = subjects # in case there are no excluded subjects

    # option 1: one-sample t-test
    contrasts = [["mean", "T", ["intercept"], [1]]]
    level2model = pe.Node(
        interface=fsl.MultipleRegressDesign(
            regressors={"intercept": [1.0 for s in trimmed_subjects]},
            contrasts=contrasts
        ),
        name="l2model"
    )

    if covariates is not None:

        # Transform covariates dict to pandas dataframe
        df_covariates = pd.DataFrame(covariates)
        if list(excluded_subjects):
            # Read qcresults.json and exclude bad subjects from covariates and subject_groups
            df_covariates = df_covariates.drop(excluded_subjects)

            for excluded_subject in excluded_subjects:
                subject_groups.pop(excluded_subject, None)

        for covariate in df_covariates:
            # Demean covariates for flameo
            df_covariates[covariate] = df_covariates[covariate] - df_covariates[covariate].mean()
        # transform reduced covariates back to dict for later purposes
        covariates = df_covariates.to_dict()

        # add SubjectGroups and ID to header
        df_subject_group = pd.DataFrame.from_dict(subject_groups, orient='index', columns=['SubjectGroup'])
        df_covariates = pd.concat([df_subject_group, df_covariates], axis=1, sort=True)
        df_covariates = df_covariates.reset_index()  # add id column
        df_covariates = df_covariates.rename(columns={'index': 'Subject_ID'})  # rename subject column

        # save demeaned covariates to csv
        df_covariates.to_csv(workdir + '/demeaned_covariates.csv')

        # transform to dictionary of lists
        regressors = {k: [float(v[s]) for s in trimmed_subjects] for k, v in covariates.items()}
        if (subject_groups is None) or (bool(subject_groups) is False):
            # one-sample t-test with covariates
            regressors["intercept"] = [1.0 for s in trimmed_subjects]
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
            dummies = {k: [float(v[s]) for s in trimmed_subjects] for k, v in dummies.items()}
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

    # actuallt run FSL FLAME

    if outname not in ["reho", "alff"]:
        flameo = pe.MapNode(
            interface=fsl.FLAMEO(
                run_mode=run_mode
            ),
            name="flameo",
            iterfield=["cope_file", "var_cope_file"]
        )
    else:
        flameo = pe.MapNode(
            interface=fsl.FLAMEO(
                run_mode=run_mode
            ),
            name="flameo",
            iterfield=["cope_file"]
        )

    workflow.connect([
        (inputnode, imgmerge, [
            ("imgs", "in_files")
        ]),

        (inputnode, maskmerge, [
            ("mask_files", "in_files")
        ]),
        (maskmerge, maskagg, [
            ("merged_file", "in_file")
        ]),
    ])
    if outname not in ["reho", "alff"]:
        workflow.connect([
            (inputnode, gendofimage, [
                ("imgs", "in_file"),
                (("dof_files", gen_merge_op_str), "op_string")
            ]),

            (inputnode, varcopemerge, [
                ("varcopes", "in_files")
            ]),

            (gendofimage, dofmerge, [
                ("out_file", "in_files")
            ])])

    workflow.connect([
        (imgmerge, flameo, [
            ("merged_file", "cope_file")
        ])])

    if outname not in ["reho", "alff"]:
        workflow.connect([
            (varcopemerge, flameo, [
                ("merged_file", "var_cope_file")
            ]),
            (dofmerge, flameo, [
                ("merged_file", "dof_var_cope_file")
            ])])

    workflow.connect(([
        (level2model, flameo, [
            ("design_mat", "design_file"),
            ("design_con", "t_con_file"),
            ("design_grp", "cov_split_file")
        ]),

        (flameo, outputnode, [
            (("copes", flatten), "imgs"),
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

    return workflow, contrast_names
