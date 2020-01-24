# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
import nibabel as nb

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ...interface import (
    Dof,
    MergeColumnsTSV,
    MatrixToTSV
)
from ..confounds import make_confounds_selectcolumns


def init_dualregression_wf(metadata, componentsfile,
                           name="firstlevel"):
    """
    create a workflow to calculate dual regression for ICA seeds
    :param componentsfile: 4d image file with ica components
    :param subject: name of subject this workflow belongs to
    :param output_dir: path to intermediates directory
    :param name: workflow name (Default value = "firstlevel")

    """
    workflow = pe.Workflow(name=name)

    # Get name of ICA template from workflow name
    template_name = name.replace("_dualregression_wf", "")

    # inputs are the bold file, the mask file and
    # the confounds file
    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "mask_file", "confounds"]
        ),
        name="inputnode"
    )

    # Delete zero voxels for mean time series
    maths = pe.Node(
        interface=fsl.ApplyMask(),
        name="maths",
    )
    maths.inputs.in_file = componentsfile

    # extract number of ICA components from 4d image and name them
    ncomponents = nb.load(componentsfile).shape[3]
    componentnames = ["%s_%d" % (template_name, i) for i in range(ncomponents)]

    # first step, calculate spatial regression of ICA components on to the
    # bold file
    glm0 = pe.Node(
        interface=fsl.GLM(
            out_file="beta",
            demean=True,
        ),
        name="glm0"
    )

    selectcolumns, confounds_list = make_confounds_selectcolumns(
        metadata
    )

    mergecolumns = pe.Node(
        interface=MergeColumnsTSV(2),
        name="mergecolumns"
    )

    contrasts = np.zeros((ncomponents, ncomponents+len(confounds_list)))
    contrasts[:ncomponents, :ncomponents] = np.eye(ncomponents)

    contrasttotsv = pe.Node(
        interface=MatrixToTSV(),
        name="contrast_node"
    )
    contrasttotsv.inputs.matrix = contrasts

    # second step, calculate the temporal regression of the time series
    # from the first step on to the bold file
    glm1 = pe.Node(
        interface=fsl.GLM(
            out_file="beta.nii.gz",
            out_cope="cope.nii.gz",
            out_varcb_name="varcope.nii.gz",
            out_z_name="zstat.nii.gz",
            demean=True
        ),
        name="glm1"
    )

    # split regression outputs into individual images
    splitcopesimage = pe.Node(
        interface=fsl.Split(dimension="t"),
        name="splitcopesimage"
    )
    splitvarcopesimage = pe.Node(
        interface=fsl.Split(dimension="t"),
        name="splitvarcopesimage"
    )
    splitzstatsimage = pe.Node(
        interface=fsl.Split(dimension="t"),
        name="splitzstatsimage"
    )

    # generate dof text file
    gendoffile = pe.Node(
        interface=Dof(num_regressors=1),
        name="gendoffile"
    )

    # outputs are cope, varcope and zstat for each seed region and a dof_file
    varnames = sum(
        [["%s_stat" % componentname, "%s_var" % componentname,
          "%s_zstat" % componentname, "%s_dof_file" % componentname]
         for componentname in componentnames], []
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=varnames,
        ),
        name="outputnode"
    )

    # split regression outputs by name
    splitcopes = pe.Node(
        interface=niu.Split(splits=[1 for componentname in componentnames]),
        name="splitcopes"
    )
    splitvarcopes = pe.Node(
        interface=niu.Split(splits=[1 for componentname in componentnames]),
        name="splitvarcopes"
    )
    splitzstats = pe.Node(
        interface=niu.Split(splits=[1 for componentname in componentnames]),
        name="splitzstats"
    )

    workflow.connect([
        (inputnode, maths, [
            ("mask_file", "mask_file")
        ]),
        (maths, glm0, [
            ("out_file", "design"),
        ]),
        (inputnode, glm0, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (inputnode, glm1, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (glm0, mergecolumns, [
            ("out_file", "in1")
        ]),
        (inputnode, selectcolumns, [
            ("confounds", "in_file"),
        ]),
        (selectcolumns, mergecolumns, [
            ("out_file", "in2"),
        ]),
        (mergecolumns, glm1, [
            ("out_file", "design")
        ]),
        (contrasttotsv, glm1, [
            ("out_file", "contrasts")
        ]),

        (glm1, splitcopesimage, [
            ("out_cope", "in_file"),
        ]),
        (glm1, splitvarcopesimage, [
            ("out_varcb", "in_file"),
        ]),
        (glm1, splitzstatsimage, [
            ("out_z", "in_file"),
        ]),
        (splitcopesimage, splitcopes, [
            ("out_files", "inlist"),
        ]),
        (splitvarcopesimage, splitvarcopes, [
            ("out_files", "inlist"),
        ]),
        (splitzstatsimage, splitzstats, [
            ("out_files", "inlist"),
        ]),

        (inputnode, gendoffile, [
            ("bold_file", "in_file"),
        ]),
        (gendoffile, outputnode, [
            ("out_file", "dof_file"),
        ]),
    ])

    # connect outputs named for the ICA components
    for i, componentname in enumerate(componentnames):
        workflow.connect([
            (splitcopes, outputnode, [
                ("out%i" % (i + 1), "%s_stat" % componentname)
            ]),
            (splitvarcopes, outputnode, [
                ("out%i" % (i + 1), "%s_var" % componentname)
            ]),
            (splitzstats, outputnode, [
                ("out%i" % (i + 1), "%s_zstat" % componentname)
            ]),
            (gendoffile, outputnode, [
                ("out_file", "%s_dof_file" % componentname)
            ]),
        ])

    outfields = ["stat", "var", "zstat", "dof_file"]

    return workflow, componentnames, outfields
