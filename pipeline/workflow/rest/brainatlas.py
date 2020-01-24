# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl


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
        fields=["bold_file", "mask_file"]),
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
    def get_brain_atlas_label_string(in_file):
        label_commands = []
        for atlas in in_file:
            label_commands.append(f"--label={atlas}")
        return label_commands

    meants = pe.MapNode(
        interface=fsl.ImageMeants(),
        name="meants",
        iterfield=["args"]
    )

    outputnode = pe.Node(niu.IdentityInterface(
        fields=["brainatlas_matrix_file"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, design_node, [
            ("movpar_file", "movpar_file"),
            ("csf_wm_meants_file", "csf_wm_meants_file"),
            ("gs_meants_file", "gs_meants_file"),
        ]),
        (inputnode, glm, [
            ("bold_file", "in_file"),
        ]),
        (design_node, glm, [
            ("design", "design"),
        ]),
        (inputnode, maths, [
            ("mask_file", "mask_file")
        ]),
        (glm, meants, [
            ("out_res", "in_file")
        ]),
        (maths, brain_atlas_label_string, [
            ("out_file", "in_file")
        ]),
        (brain_atlas_label_string, meants, [
            ("label_string", "args")
        ]),
        (meants, outputnode, [
            ("out_file", "brainatlas_matrix_file"),
        ]),
    ])

    outfields = []

    return workflow, atlasnames, outfields
