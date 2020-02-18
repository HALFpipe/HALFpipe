# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from ...interface import ConnectivityMeasure
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
        fields=["bold_file", "mask_file"]),
        name="inputnode"
    )

    if "BrainAtlasImage" not in metadata:
        return workflow, [], []

    atlases = metadata["BrainAtlasImage"]

    atlasnames = list(atlases.keys())
    atlas_files = [atlases[k] for k in atlasnames]

    connectivitymeasure = pe.MapNode(
        interface=ConnectivityMeasure(
            kind="correlation",
            resampling_target="labels",
            atlas_type="labels",
            standardize=False
        ),
        name="connectivitymeasure",
        iterfield=["atlas_file"]
    )
    connectivitymeasure.inputs.atlas_file = atlas_files

    splitconnectivity = pe.Node(
        interface=niu.Split(splits=[1 for atlasname in atlasnames]),
        name="splitconnectivity"
    )
    splittimeseries = pe.Node(
        interface=niu.Split(splits=[1 for atlasname in atlasnames]),
        name="splittimeseries"
    )

    outputnode = pe.Node(niu.IdentityInterface(
        fields=["{}_connectivity".format(atlasname)
                for atlasname in atlasnames] +
        ["{}_timeseries".format(atlasname) for atlasname in atlasnames]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, connectivitymeasure, [
            ("bold_file", "in_file"),
            ("mask_file", "mask_file")
        ]),
        (connectivitymeasure, splitconnectivity, [
            ("connectivity", "inlist"),
        ]),
        (connectivitymeasure, splittimeseries, [
            ("timeseries", "inlist"),
        ])
    ])

    # connect outputs named for the atlases
    for i, atlasname in enumerate(atlasnames):
        workflow.connect([
            (splitconnectivity, outputnode, [
                (("out%i" % (i + 1), _get_first),
                    "%s_connectivity" % atlasname)
            ]),
            (splittimeseries, outputnode, [
                (("out%i" % (i + 1), _get_first),
                    "%s_timeseries" % atlasname)
            ]),
        ])

    outfields = ["connectivity", "timeseries"]

    return workflow, atlasnames, outfields
