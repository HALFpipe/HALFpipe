# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ...utils import _get_first


def init_brainatlas_wf(metadata, name="brainatlas"):
    """
    create workflow for brainatlas
    :param use_mov_pars: regression - Movement parameters
    :param use_csf: regression - CSF
    :param use_white_matter: regression - White Matter
    :param use_global_signal: regression - Global Signal
    :param subject:
    :param atlases: dictionary of filenames by user-defined names
        of atlases
    :param name: workflow name (Default value = "firstlevel")

    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds"]),
        name="inputnode"
    )

    if "BrainAtlasImage" not in metadata:
        return workflow, [], []

    atlases = metadata["BrainAtlasImage"]

    atlasnames = list(atlases.keys())
    atlas_paths = [atlases[k] for k in atlasnames]

    maths = pe.MapNode(
        interface=fsl.ApplyMask(),
        name="maths",
        iterfield=["in_file"]
    )
    maths.inputs.in_file = atlas_paths

    # Creates label string for fslmeants
    def make_brainatlas_label_arg(in_file):
        label_commands = []
        for atlas in in_file:
            label_commands.append(f"--label={atlas}")
        return label_commands

    meants = pe.MapNode(
        interface=fsl.ImageMeants(),
        name="meants",
        iterfield=["args"]
    )

    splitmatrices = pe.Node(
        interface=niu.Split(splits=[1 for atlasname in atlasnames]),
        name="splitmatrices"
    )

    outputnode = pe.Node(niu.IdentityInterface(
        fields=["{}_matrix".format(atlasname)
                for atlasname in atlasnames]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, maths, [
            ("mask_file", "mask_file")
        ]),
        (inputnode, meants, [
            ("bold_file", "in_file")
        ]),
        (maths, meants, [
            (("out_file", make_brainatlas_label_arg), "args")
        ]),
        (meants, splitmatrices, [
            ("out_file", "inlist"),
        ]),
    ])

    # connect outputs named for the atlases
    for i, atlasname in enumerate(atlasnames):
        workflow.connect([
            (splitmatrices, outputnode, [
                (("out%i" % (i + 1), _get_first), "%s_matrix" % atlasname)
            ]),
        ])

    outfields = ["matrix"]

    return workflow, atlasnames, outfields
