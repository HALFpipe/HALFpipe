# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ..interface import GroupDesign

from ..utils import flatten


def gen_merge_op_str(fileNames):
    """
    generate string argument to FSLMATHS that creates a dof image
    file from a dof text file

    :param fileNames: dof text file

    """
    out = []
    for fileName in fileNames:
        with open(fileName) as file:
            text = file.read()
        out.append("-abs -bin -mul %f" % float(text))
    return out


def get_len(arr):
    """
    wrapper around len

    :param arr: array

    """
    return len(arr)


def init_higherlevel_wf(fieldnames,
                        group_data, run_mode="flame1", name="higherlevel"):
    """

    :param run_mode: mode argument passed to FSL FLAMEO
        (Default value = "flame1")
    :param name: workflow name (Default value = "higherlevel")
    :param subjects: list of subject names (Default value = None)
    :param covariates: two-level dictionary of covariates by name
        and subject (Default value = None)
    :param subject_groups: dictionary of subjects by group
        (Default value = None)
    :param group_contrasts: two-level dictionary of contrasts by contrast
        name and values by group (Default = None)
    :param outname: names of inputs for higherlevel workflow,
        names of outputs from firstlevel workflow
    :param workdir: the working directory to check for qualitycheck excludes
    :param task: name of task to filter excludes FIXME this
        shouldn"t be necessary, go by filename instead

    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=fieldnames
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=[
                "copes", "varcopes", "zstats", "dof_files", "mask_file",
                "contrast_names"
            ]
        ),
        name="outputnode"
    )

    if "subject" not in fieldnames:
        return
    if "stat" not in fieldnames:
        return
    if "mask_file" not in fieldnames:
        return

    flame_iterfields = ["cope_file"]
    if "var" in fieldnames:
        flame_iterfields.append("varcope_file")
    flameo = pe.MapNode(
        interface=fsl.FLAMEO(
            run_mode=run_mode
        ),
        name="flameo",
        iterfield=flame_iterfields
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
    workflow.connect([
        (inputnode, maskmerge, [
            ("mask_file", "in_files")
        ]),
        (maskmerge, maskagg, [
            ("merged_file", "in_file")
        ]),
        (maskagg, flameo, [
            ("out_file", "mask_file")
        ]),
        (maskagg, outputnode, [
            ("out_file", "mask_file")
        ]),
    ])

    # merge all input nii image files to one big nii file
    statmerge = pe.Node(
        interface=fsl.Merge(dimension="t"),
        name="statmerge"
    )
    workflow.connect([
        (inputnode, statmerge, [
            ("stat", "in_files")
        ]),
        (statmerge, flameo, [
            ("merged_file", "cope_file")
        ])
    ])

    if "var" in fieldnames:
        # merge all input nii image files to one big nii file
        varmerge = pe.Node(
            interface=fsl.Merge(dimension="t"),
            name="varmerge"
        )
        workflow.connect([
            (inputnode, varmerge, [
                ("var", "in_files")
            ]),
            (varmerge, flameo, [
                ("merged_file", "var_cope_file")
            ]),
        ])

    if "dof_file" in fieldnames:
        # we get a text dof_file, but need to transform it to an nii image
        gendofimage = pe.MapNode(
            interface=fsl.ImageMaths(),
            iterfield=["in_file", "op_string"],
            name="gendofimage"
        )
        # merge all generated nii image files to one big nii file
        dofmerge = pe.Node(
            interface=fsl.Merge(dimension="t"),
            name="dofmerge"
        )
        workflow.connect([
            (inputnode, gendofimage, [
                ("stat", "in_file"),
                (("dof_file", gen_merge_op_str), "op_string")
            ]),
            (gendofimage, dofmerge, [
                ("out_file", "in_files")
            ]),
            (dofmerge, flameo, [
                ("merged_file", "dof_var_cope_file")
            ])
        ])

    design = pe.Node(
        interface=GroupDesign(),
        name="group_design"
    )
    design.inputs.data = group_data

    level2model = pe.Node(
        interface=fsl.MultipleRegressDesign(),
        name="l2model"
    )

    workflow.connect([
        (inputnode, design, [
            ("subject", "subjects")
        ]),

        (design, level2model, [
            ("regressors", "regressors"),
            ("contrasts", "contrasts"),
        ]),

        (design, outputnode, [
            ("contrast_names", "contrast_names")
        ]),

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
    ])

    return workflow
