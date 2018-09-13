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

def init_firstlevel_wf(conditions, 
        contrasts, repetition_time, 
        use_mov_pars, name = "firstlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file", "mask_file", "confounds_file"]), 
        name = "inputnode"
    )

    names = list(conditions.keys())
    onsets = [conditions[k]["onsets"] for k in names]
    durations = [conditions[k]["durations"] for k in names]

    modelspec = pe.Node(
        interface = model.SpecifyModel(
            input_units = "secs",
            high_pass_filter_cutoff = 128., time_repetition = repetition_time,
            subject_info = Bunch(conditions = names, 
                onsets = onsets, durations = durations)
        ), 
        name = "modelspec"
    )
    
    contrasts_ = [[k, "T"] + [list(i) for i in zip(*[(n, val) for n, val in v.items()])] for k, v in contrasts.items()]

    connames = [k[0] for k in contrasts_]
    outputnode._interface.names = connames

    level1design = pe.Node(
        interface = fsl.Level1Design(
            contrasts = contrasts_,
            interscan_interval = repetition_time,
            model_serial_correlations = True,
            bases = {"dgamma": {"derivs": False}}
        ), 
        name = "level1design"
    )

    modelgen = pe.Node(
        interface = fsl.FEATModel(),
        name = "modelgen",
        iterfield = ["fsf_file", "ev_files"]
    )
    
    stats = pe.Node(
        interface = fsl.ImageStats(op_string = "-R"),
        name = "stats"
    )

    modelestimate = pe.Node(
        interface = fsl.FILMGLS(smooth_autocorr = True, 
            mask_size = 5),
        name = "modelestimate",
        iterfield=["design_file", "in_file", "tcon_file"]
    )
    
    maskcopes = pe.MapNode(
        interface = fsl.ApplyMask(),
        name = "maskcopes",
        iterfield = ["in_file"]
    )
    maskvarcopes = pe.MapNode(
        interface = fsl.ApplyMask(),
        name = "maskvarcopes",
        iterfield = ["in_file"]
    )
    maskzstats = pe.MapNode(
        interface = fsl.ApplyMask(),
        name = "maskzstats",
        iterfield = ["in_file"]
    )
    
    splitcopes = pe.Node(
        interface = niu.Split(splits = [1 for conname in connames]),
        name = "splitcopes"
    )
    splitvarcopes = pe.Node(
        interface = niu.Split(splits = [1 for conname in connames]),
        name = "splitvarcopes"
    )
    splitzstats = pe.Node(
        interface = niu.Split(splits = [1 for conname in connames]),
        name = "splitzstats"
    )

    outputnode = pe.Node(niu.IdentityInterface(
        fields = sum([["%s_cope" % conname, 
                "%s_varcope" % conname, "%s_zstat" % conname] 
            for conname in connames], []) + ["dof_file"]), 
        name = "outputnode"
    )
    
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
    
    for i, conname in enumerate(connames):
        workflow.connect(splitcopes, "out%i" % (i+1), outputnode, "%s_cope" % conname)
        workflow.connect(splitvarcopes, "out%i" % (i+1), outputnode, "%s_varcope" % conname)
        workflow.connect(splitzstats, "out%i" % (i+1), outputnode, "%s_zstat" % conname)
    
    return workflow, connames
