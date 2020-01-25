# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.algorithms.modelgen as model

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl
from nipype.interfaces.base import Bunch

from ...utils import (
    _ravel,
    _get_first
)
from ..confounds import make_confounds_selectcolumns


def _get_float(input):
    def flatten(l):
        if isinstance(l, str) or isinstance(l, float):
            return [l]
        else:
            o = []
            for k in l:
                o += flatten(k)
            return o
    return float(flatten(input)[0])


def init_glm_wf(metadata, conditions,
                name="glm"):
    """
    create workflow to calculate a first level glm for task functional data

    :param conditions: dictionary of conditions with onsets and durations
        by condition names
    :param contrasts: dictionary of contrasts by names
    :param repetition_time: repetition time
    :param use_movpars: if true, regress out movement parameters when
        calculating the glm
    :param use_csf: if true, regress out csf parameters when
        calculating the glm
    :param use_wm: if true, regress out white matter parameters when
        calculating the glm
    :param use_globalsignal: if true, regress out global signal parameters
        when calculating the glm
    :param name: workflow name (Default value = "glm")

    """

    workflow = pe.Workflow(name=name)

    if "Contrasts" not in metadata:
        return workflow, [], []
    if "RepetitionTime" not in metadata:
        return workflow, [], []
    contrasts = metadata["Contrasts"]
    repetition_time = metadata["RepetitionTime"]

    if conditions is None or len(conditions) == 0:
        return workflow, [], []

    # inputs are the bold file, the mask file and the confounds file
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds"]),
        name="inputnode"
    )

    # transform (unordered) conditions dictionary into three (ordered) lists

    names = list(conditions.keys())
    onsets = [conditions[k]["onsets"] for k in names]
    durations = [conditions[k]["durations"] for k in names]

    selectcolumns, _ = make_confounds_selectcolumns(
        metadata
    )

    # first level model specification
    modelspec = pe.Node(
        interface=model.SpecifyModel(
            input_units="secs",
            high_pass_filter_cutoff=128., time_repetition=repetition_time,
            subject_info=Bunch(conditions=names,
                               onsets=onsets, durations=durations)
        ),
        name="modelspec"
    )

    # transform contrasts dictionary to nipype list data structure
    contrasts_ = [
        [k, "T"] +
        [list(i) for i in zip(*[(n, val) for n, val in v.items()])]
        for k, v in contrasts.items()
    ]

    connames = [k[0] for k in contrasts_]

    # generate design from first level specification
    level1design = pe.Node(
        interface=fsl.Level1Design(
            contrasts=contrasts_,
            interscan_interval=repetition_time,
            model_serial_correlations=True,
            bases={"dgamma": {"derivs": False}}
        ),
        name="level1design"
    )

    # generate required input files for FILMGLS from design
    modelgen = pe.Node(
        interface=fsl.FEATModel(),
        name="modelgen",
        iterfield=["fsf_file", "ev_files"]
    )

    # calculate range of image values to determine cutoff value
    # for FILMGLS
    stats = pe.Node(
        interface=fsl.ImageStats(op_string="-R"),
        name="stats"
    )

    # actually estimate the first level model
    modelestimate = pe.Node(
        interface=fsl.FILMGLS(smooth_autocorr=True,
                              mask_size=5),
        name="modelestimate",
        iterfield=["design_file", "in_file", "tcon_file"]
    )

    # mask regression outputs
    maskcopes = pe.MapNode(
        interface=fsl.ApplyMask(),
        name="maskcopes",
        iterfield=["in_file"]
    )
    maskvarcopes = pe.MapNode(
        interface=fsl.ApplyMask(),
        name="maskvarcopes",
        iterfield=["in_file"]
    )
    maskzstats = pe.MapNode(
        interface=fsl.ApplyMask(),
        name="maskzstats",
        iterfield=["in_file"]
    )

    # split regression outputs by name
    splitcopes = pe.Node(
        interface=niu.Split(splits=[1 for conname in connames]),
        name="splitcopes"
    )
    splitvarcopes = pe.Node(
        interface=niu.Split(splits=[1 for conname in connames]),
        name="splitvarcopes"
    )
    splitzstats = pe.Node(
        interface=niu.Split(splits=[1 for conname in connames]),
        name="splitzstats"
    )

    # outputs are cope, varcope and zstat for each contrast and a dof_file
    outputnode = pe.Node(niu.IdentityInterface(
        fields=sum([
            ["%s_stat" % conname,
             "%s_var" % conname,
             "%s_zstat" % conname,
             "%s_dof_file" % conname] for conname in connames
        ], [])),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, selectcolumns, [
            ("confounds", "in_file")
        ]),
        (selectcolumns, modelspec, [
            ("out_file", "realignment_parameters")
        ]),

        (inputnode, modelspec, [
            ("bold_file", "functional_runs")
        ]),
        (inputnode, modelestimate, [
            ("bold_file", "in_file")
        ]),
        (modelspec, level1design, [
            ("session_info", "session_info")
        ]),
        (level1design, modelgen, [
            ("fsf_files", "fsf_file"),
            ("ev_files", "ev_files")
        ]),

        (inputnode, stats, [
            ("bold_file", "in_file")
        ]),
        (stats, modelestimate, [
            (("out_stat", _get_float), "threshold")
        ]),
        (modelgen, modelestimate, [
            ("design_file", "design_file"),
            ("con_file", "tcon_file")
        ]),

        (inputnode, maskcopes, [
            ("mask_file", "mask_file")
        ]),
        (inputnode, maskvarcopes, [
            ("mask_file", "mask_file")
        ]),
        (inputnode, maskzstats, [
            ("mask_file", "mask_file")
        ]),

        (modelestimate, maskcopes, [
            (("copes", _ravel), "in_file"),
        ]),
        (modelestimate, maskvarcopes, [
            (("varcopes", _ravel), "in_file"),
        ]),
        (modelestimate, maskzstats, [
            (("zstats", _ravel), "in_file"),
        ]),

        (maskcopes, splitcopes, [
            ("out_file", "inlist"),
        ]),
        (maskvarcopes, splitvarcopes, [
            ("out_file", "inlist"),
        ]),
        (maskzstats, splitzstats, [
            ("out_file", "inlist"),
        ]),
    ])

    # connect outputs named for the contrasts
    for i, conname in enumerate(connames):
        workflow.connect([
            (splitcopes, outputnode, [
                (("out%i" % (i + 1), _get_first), "%s_stat" % conname)
            ]),
            (splitvarcopes, outputnode, [
                (("out%i" % (i + 1), _get_first), "%s_var" % conname)
            ]),
            (splitzstats, outputnode, [
                (("out%i" % (i + 1), _get_first), "%s_zstat" % conname)
            ]),
            (modelestimate, outputnode, [
                ("dof_file", "%s_dof_file" % conname)
            ]),
        ])

    outfields = ["stat", "var", "zstat", "dof_file"]

    return workflow, connames, outfields
