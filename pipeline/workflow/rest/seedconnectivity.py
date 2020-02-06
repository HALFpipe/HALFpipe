# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ...interface import (
    Dof,
    MergeColumnsTSV,
    MatrixToTSV
)
from ..confounds import make_confounds_selectcolumns
from ...utils import _get_first


def init_seedconnectivity_wf(metadata,
                             name="seedconnectivity"):
    """
    create workflow to calculate seed connectivity maps
    for resting state functional scans

    :param seeds: dictionary of filenames by user-defined names
        of binary masks that define the seed regions
    :param use_mov_pars: if true, regress out movement parameters when
        calculating the glm
    :param use_csf: if true, regress out csf parameters when
        calculating the glm
    :param use_wm: if true, regress out white matter parameters when
        calculating the glm
    :param use_globalsignal: if true, regress out global signal parameters when
        calculating the glm
    :param name: workflow name (Default value = "firstlevel")

    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "mask_file", "confounds"]
        ),
        name="inputnode"
    )

    if "ConnectivitySeeds" not in metadata:
        return workflow, [], []

    seeds = metadata["ConnectivitySeeds"]

    # make two (ordered) lists from (unordered) dictionary of seeds
    seednames = list(seeds.keys())  # contains the keys (seed names)
    seed_paths = [seeds[k] for k in seednames]  # contains the filenames

    maths = pe.MapNode(
        interface=fsl.ApplyMask(),
        name="maths",
        iterfield=["in_file"]
    )
    maths.inputs.in_file = seed_paths

    # calculate the mean time series of the region defined by each mask
    meants = pe.MapNode(
        interface=fsl.ImageMeants(),
        name="meants",
        iterfield=["mask"]
    )

    selectcolumns, confounds_list = make_confounds_selectcolumns(
        metadata
    )

    mergecolumns = pe.MapNode(
        interface=MergeColumnsTSV(2),
        name="mergecolumns",
        iterfield=["in1"]
    )

    contrast = np.zeros((1, len(confounds_list)+1))
    contrast[0, 0] = 1

    contrasttotsv = pe.Node(
        interface=MatrixToTSV(),
        name="contrast_node"
    )
    contrasttotsv.inputs.matrix = contrast

    # calculate the regression of the mean time series
    # onto the functional image.
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
    splitcopes = pe.Node(
        interface=niu.Split(splits=[1 for seedname in seednames]),
        name="splitcopes"
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
    varnames = sum(
        [["%s_stat" % seedname, "%s_var" % seedname,
          "%s_zstat" % seedname, "%s_dof_file" % seedname]
         for seedname in seednames], []
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=varnames,
        ),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, maths, [
            ("mask_file", "mask_file")
        ]),
        (maths, meants, [
            ("out_file", "mask")
        ]),
        (inputnode, meants, [
            ("bold_file", "in_file")
        ]),
        (inputnode, glm, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (meants, mergecolumns, [
            ("out_file", "in1"),
        ]),
        (inputnode, selectcolumns, [
            ("confounds", "in_file"),
        ]),
        (selectcolumns, mergecolumns, [
            ("out_file", "in2"),
        ]),
        (mergecolumns, glm, [
            ("out_file", "design")
        ]),
        (contrasttotsv, glm, [
            ("out_file", "contrasts")
        ]),

        (glm, splitcopes, [
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
    ])

    # connect outputs named for the seeds
    for i, seedname in enumerate(seednames):
        workflow.connect([
            (splitcopes, outputnode, [
                (("out%i" % (i + 1), _get_first), "%s_stat" % seedname)
            ]),
            (splitvarcopes, outputnode, [
                (("out%i" % (i + 1), _get_first), "%s_var" % seedname)
            ]),
            (splitzstats, outputnode, [
                (("out%i" % (i + 1), _get_first), "%s_zstat" % seedname)
            ]),
            (gendoffile, outputnode, [
                ("out_file", "%s_dof_file" % seedname)
            ]),
        ])

    outfields = ["stat", "var", "zstat", "dof_file"]

    return workflow, seednames, outfields
