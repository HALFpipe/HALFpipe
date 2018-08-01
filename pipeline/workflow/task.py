# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.algorithms.modelgen as model
from nipype.interfaces.base import Bunch

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ..utils import flatten

def get_thr(input):
    return float(flatten(input)[0])

def init_firstlevel_wf(conditions, 
        contrasts, repetition_time, 
        use_mov_pars, name = "firstlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file", "mask_file", "confounds_file"]), 
        name = "inputnode"
    )
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = ["names", "copes", "varcopes", "zstats", "dof_file"]), 
        name = "outputnode"
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
            (("out_stat", get_thr), "threshold")
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
        (maskcopes, outputnode, [
            ("out_file", "copes"), 
        ]),
        (maskvarcopes, outputnode, [
            ("out_file", "varcopes"), 
        ]),
        (maskzstats, outputnode, [
            ("out_file", "zstats"), 
        ]),
        (modelestimate, outputnode, [
            ("dof_file", "dof_file")
        ]),
    ])
    
    return workflow, connames
