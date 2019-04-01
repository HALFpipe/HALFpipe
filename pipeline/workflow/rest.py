# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import nibabel as nib

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from fmriprep.interfaces.bids import _splitext

from .reho import compute_reho

from ..interface import Dof


def init_seedconnectivity_wf(seeds,
                             use_mov_pars, name="firstlevel"):
    """
    create workflow to calculate seed connectivity maps
    for resting state functional scans

    :param seeds: dictionary of filenames by user-defined names 
        of binary masks that define the seed regions
    :param use_mov_pars: if true, regress out movement parameters when 
        calculating seed connectivity
    :param name: workflow name (Default value = "firstlevel")

    """
    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the confounds file 
    # that contains the movement parameters
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds_file"]),
        name="inputnode"
    )

    # make two (ordered) lists from (unordered) dictionary of seeds
    seednames = list(seeds.keys())  # contains the keys (seed names)
    seed_paths = [seeds[k] for k in seednames]  # contains the values (filenames)

    # calculate the mean time series of the region defined by each mask
    meants = pe.MapNode(
        interface=fsl.ImageMeants(),
        name="meants",
        iterfield=["mask"]
    )
    meants.inputs.mask = seed_paths

    # calculate the regression of the mean time series onto the functional image
    # the result is the seed connectivity map
    glm = pe.MapNode(
        interface=fsl.GLM(
            out_file="beta.nii.gz",
            out_cope="cope.nii.gz",
            out_varcb_name="varcope.nii.gz",
            out_z_name="zstat.nii.gz",
            demean=True
        ),
        name="glm",
        iterfield=["design"]
    )

    # generate dof text file
    gendoffile = pe.Node(
        interface=Dof(num_regressors=1),
        name="gendoffile"
    )

    # split regression outputs by name
    splitimgs = pe.Node(
        interface=niu.Split(splits=[1 for seedname in seednames]),
        name="splitimgs"
    )
    splitvarcopes = pe.Node(
        interface=niu.Split(splits=[1 for seedname in seednames]),
        name="splitvarcopes"
    )
    splitzstats = pe.Node(
        interface=niu.Split(splits=[1 for seedname in seednames]),
        name="splitzstats"
    )

    # outputs are cope, varcope and zstat for each seed region and a dof_file
    outputnode = pe.Node(niu.IdentityInterface(
        fields=sum([["%s_img" % seedname,
                     "%s_varcope" % seedname, "%s_zstat" % seedname]
                    for seedname in seednames], []) + ["dof_file"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, meants, [
            ("bold_file", "in_file")
        ]),
        (inputnode, glm, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (meants, glm, [
            ("out_file", "design")
        ]),

        (glm, splitimgs, [
            ("out_cope", "inlist"),
        ]),
        (glm, splitvarcopes, [
            ("out_varcb", "inlist"),
        ]),
        (glm, splitzstats, [
            ("out_z", "inlist"),
        ]),

        (inputnode, gendoffile, [
            ("bold_file", "in_file"),
        ]),
        (gendoffile, outputnode, [
            ("out_file", "dof_file"),
        ]),
    ])

    # connect outputs named for the seeds
    for i, seedname in enumerate(seednames):
        workflow.connect(splitimgs, "out%i" % (i + 1), outputnode, "%s_img" % seedname)
        workflow.connect(splitvarcopes, "out%i" % (i + 1), outputnode, "%s_varcope" % seedname)
        workflow.connect(splitzstats, "out%i" % (i + 1), outputnode, "%s_zstat" % seedname)

    return workflow, seednames


def init_dualregression_wf(componentsfile,
                           use_mov_pars, name="firstlevel"):
    """
    create a workflow to calculate dual regression for ICA seeds

    :param componentsfile: 4d image file with ica components
    :param use_mov_pars: if true, regress out movement parameters when 
        calculating dual regression
    :param name: workflow name (Default value = "firstlevel")

    """
    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the confounds file 
    # that contains the movement parameters
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds_file"]),
        name="inputnode"
    )

    # extract number of ICA components from 4d image and name them
    ncomponents = nib.load(componentsfile).shape[3]
    fname, _ = _splitext(os.path.basename(componentsfile))
    componentnames = ["%s_%d" % (fname, i) for i in range(ncomponents)]

    # first step, calculate spatial regression of ICA components on to the
    # bold file
    glm0 = pe.Node(
        interface=fsl.GLM(
            out_file="beta",
            demean=True
        ),
        name="glm0"
    )
    glm0.inputs.design = componentsfile

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
    splitimgsimage = pe.Node(
        interface=fsl.Split(dimension="t"),
        name="splitimgsimage"
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

    # outputs are cope, varcope and zstat for each ICA component and a dof_file
    outputnode = pe.Node(niu.IdentityInterface(
        fields=sum([["%s_img" % componentname,
                     "%s_varcope" % componentname, "%s_zstat" % componentname]
                    for componentname in componentnames], []) + ["dof_file"]),
        name="outputnode"
    )

    # split regression outputs by name
    splitimgs = pe.Node(
        interface=niu.Split(splits=[1 for componentname in componentnames]),
        name="splitimgs"
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
        (inputnode, glm0, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (inputnode, glm1, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (glm0, glm1, [
            ("out_file", "design")
        ]),

        (glm1, splitimgsimage, [
            ("out_cope", "in_file"),
        ]),
        (glm1, splitvarcopesimage, [
            ("out_varcb", "in_file"),
        ]),
        (glm1, splitzstatsimage, [
            ("out_z", "in_file"),
        ]),
        (splitimgsimage, splitimgs, [
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
        workflow.connect(splitimgs, "out%i" % (i + 1), outputnode, "%s_img" % componentname)
        workflow.connect(splitvarcopes, "out%i" % (i + 1), outputnode, "%s_varcope" % componentname)
        workflow.connect(splitzstats, "out%i" % (i + 1), outputnode, "%s_zstat" % componentname)

    return workflow, componentnames


def init_reho_wf(name="firstlevel"):
    """
    create a workflow to do ReHo and ALFF

    """
    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the cluster size
    # that contains the movement parameters
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds_file"]),
        name="inputnode"
    )

    reho_imports = ['import os', 'import sys', 'import nibabel as nb',
                    'import numpy as np',
                    'from pipeline.workflow.reho import f_kendall']
    raw_reho_map = pe.Node(niu.Function(input_names=['in_file', 'mask_file',
                                                     'cluster_size'],
                                        output_names=['out_file'],
                                        function=compute_reho,
                                        imports=reho_imports),
                           name='reho_img')

    raw_reho_map.inputs.cluster_size = 27

    # outputs are cope, varcope and zstat for each ICA component and a dof_file
    outputnode = pe.Node(niu.IdentityInterface(
        fields=["reho_img"]),
        name="outputnode"
    )

    # # generate dof text file
    # gendoffile = pe.Node(
    #     interface=Dof(num_regressors=1),
    #     name="gendoffile"
    # )
    # workflow.connect([
    #     (inputnode, gendoffile, [
    #         ("bold_file", "in_file"),
    #     ]),
    #     (gendoffile, outputnode, [
    #         ("out_file", "dof_file"),
    #     ])
    # ])

    workflow.connect(inputnode, 'bold_file', raw_reho_map, 'in_file')
    workflow.connect(inputnode, 'mask_file', raw_reho_map, 'mask_file')
    workflow.connect(raw_reho_map, 'out_file', outputnode, 'reho_img')
    # workflow.connect(raw_reho_map, 'out_file', outputnode, 'reho_z_score')

    return workflow


def init_brain_atlas_wf(atlases, name="firstlevel"):
    """
    create workflow to calculate seed connectivity maps
    for resting state functional scans

    :param atlases: dictionary of filenames by user-defined names
        of atlases
    :param name: workflow name (Default value = "firstlevel")

    """
    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the confounds file
    # that contains the movement parameters
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds_file"]),
        name="inputnode"
    )

    # make two (ordered) lists from (unordered) dictionary of seeds
    atlasnames = list(atlases.keys())  # contains the keys (seed names)
    atlas_args = ['--label=' + atlases[k] for k in atlasnames]  # contains the values (filenames)

    # calculate the mean time series of the region defined by each mask
    meants = pe.MapNode(
        interface=fsl.ImageMeants(),
        name="meants",
        iterfield=["args"]
    )
    meants.inputs.args = atlas_args

    # outputs are cope, varcope and zstat for each seed region and a dof_file
    outputnode = pe.Node(niu.IdentityInterface(
        fields=["brainatlas_matrix_file"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, meants, [
            ("bold_file", "in_file")
        ]),
        (meants, outputnode, [
            ("out_file", "brainatlas_matrix_file"),
        ]),
    ])

    # # connect outputs named for the seeds
    # for i, atlasname in enumerate(atlasnames):
    #     workflow.connect(splitimgs, "out%i" % (i + 1), outputnode, "%s_img" % atlasname)

    return workflow, atlasnames
