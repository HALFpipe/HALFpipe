# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.algorithms.modelgen as model
from nipype.interfaces.base import Bunch

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ..utils import (
    flatten,
    get_float
)


def init_glm_wf(conditions,
                contrasts, repetition_time,
                use_mov_pars, name="glm"):
    """
    create workflow to calculate a first level glm for task functional data

    :param conditions: dictionary of conditions with onsets and durations 
        by condition names
    :param contrasts: dictionary of contrasts by names
    :param repetition_time: repetition time
    :param use_mov_pars: if true, regress out movement parameters when 
        calculating the glm
    :param name: workflow name (Default value = "glm")

    """
    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the confounds file 
    # that contains the movement parameters
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds_file"]),
        name="inputnode"
    )

    # transform (unordered) conditions dictionary into three (ordered) lists
    names = list(conditions.keys())
    onsets = [conditions["onsets"]]
    durations = [conditions["durations"]]

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
    contrasts_ = [[k, "T"] + [list(i) for i in zip(*[(n, val) for n, val in v.items()])] for k, v in contrasts.items()]

    connames = [k[0] for k in contrasts_]

    # outputs are cope, varcope and zstat for each contrast and a dof_file
    outputnode = pe.Node(niu.IdentityInterface(
        fields=sum([["%s_img" % conname,
                     "%s_varcope" % conname, "%s_zstat" % conname]
                    for conname in connames], []) + ["dof_file"]),
        name="outputnode"
    )

    outputnode._interface.names = connames

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

    # actuallt estimate the firsy level model
    modelestimate = pe.Node(
        interface=fsl.FILMGLS(smooth_autocorr=True,
                              mask_size=5),
        name="modelestimate",
        iterfield=["design_file", "in_file", "tcon_file"]
    )

    # mask regression outputs 
    maskimgs = pe.MapNode(
        interface=fsl.ApplyMask(),
        name="maskimgs",
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
    splitimgs = pe.Node(
        interface=niu.Split(splits=[1 for conname in connames]),
        name="splitimgs"
    )
    splitvarcopes = pe.Node(
        interface=niu.Split(splits=[1 for conname in connames]),
        name="splitvarcopes"
    )
    splitzstats = pe.Node(
        interface=niu.Split(splits=[1 for conname in connames]),
        name="splitzstats"
    )

    # pass movement parameters to glm model specification if requested
    c = [("bold_file", "functional_runs")]
    if use_mov_pars:
        c.append(
            ("confounds_file", "realignment_parameters")
        )

    workflow.connect([
        (inputnode, modelspec, c),
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
            (("out_stat", get_float), "threshold")
        ]),
        (modelgen, modelestimate, [
            ("design_file", "design_file"),
            ("con_file", "tcon_file")
        ]),
        (inputnode, maskimgs, [
            ("mask_file", "mask_file")
        ]),
        (inputnode, maskvarcopes, [
            ("mask_file", "mask_file")
        ]),
        (inputnode, maskzstats, [
            ("mask_file", "mask_file")
        ]),
        (modelestimate, maskimgs, [
            (("copes", flatten), "in_file"),
        ]),
        (modelestimate, maskvarcopes, [
            (("varcopes", flatten), "in_file"),
        ]),
        (modelestimate, maskzstats, [
            (("zstats", flatten), "in_file"),
        ]),
        (modelestimate, outputnode, [
            ("dof_file", "dof_file")
        ]),

        (maskimgs, splitimgs, [
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
        workflow.connect(splitimgs, "out%i" % (i + 1), outputnode, "%s_img" % conname)
        workflow.connect(splitvarcopes, "out%i" % (i + 1), outputnode, "%s_varcope" % conname)
        workflow.connect(splitzstats, "out%i" % (i + 1), outputnode, "%s_zstat" % conname)

    return workflow, connames
