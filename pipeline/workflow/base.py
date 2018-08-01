# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import os
from os import path as op

from functools import partial
from multiprocessing import Pool

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from fmriprep.workflows.anatomical import init_anat_preproc_wf
from fmriprep.workflows.bold import init_func_preproc_wf
from fmriprep.interfaces.bids import DerivativesDataSink

from .patch import patch_wf

from .fake import FakeBIDSLayout

from .func import init_temporalfilter_wf
from .rest import init_seed_connectivity_wf
from .task import init_firstlevel_wf

from ..utils import (
    transpose,
    lookup
)

def init_workflow(workdir, keep_intermediates = True):
    workflow_file = op.join(workdir, "workflow.pklz")

    fp = op.join(workdir, "pipeline.json")

    data = None
    with open(fp, "r") as f:
        data = json.load(f)
        
    name = "intermediates"
    
    workflow = None
    if keep_intermediates:
        workflow = pe.Workflow(name = name, base_dir = workdir)
    else:
        workflow = pe.Workflow(name = name)

    images = transpose(data["images"])

    for subject, value0 in images.items():
        subject_wf = init_subject_wf((subject, value0), workdir, images, data)
        workflow.add_nodes([subject_wf])
        
    # subject_wfs = Pool().map(
    #     partial(init_subject_wf, workdir = workdir, images = images, data = data), 
    #     list(images.items())
    # )
    # workflow.add_nodes(subject_wfs)

    return workflow  

_func_inputnode_fields = ['t1_preproc', 't1_brain', 't1_mask', 't1_seg', 
    't1_tpms', 't1_aseg', 't1_aparc', 
    't1_2_mni_forward_transform', 't1_2_mni_reverse_transform', 
    'subjects_dir', 'subject_id',
    't1_2_fsnative_forward_transform', 't1_2_fsnative_reverse_transform']
    
def init_subject_wf(item, workdir, images, data):
    subject, value0 = item
    
    anat_field_names = ["T1w", "T2w", "FLAIR"]
    
    #
    # fmriprep
    #

    fmriprep_output_dir = op.join(workdir, "fmriprep_output")
    fmriprep_reportlets_dir = op.join(workdir, "fmriprep_reportlets")
    output_dir = op.join(workdir, "results")
    bids_dir = "."
    
    longitudinal = False
    t2s_coreg = False
    omp_nthreads = 1000000000
    freesurfer = False
    skull_strip_template = "OASIS"
    template = "MNI152NLin2009cAsym"
    output_spaces = ["template"]
    medial_surface_nan = False
    ignore = []
    debug = False
    low_mem = False
    anat_only = False
    hires = True
    use_bbr = True
    bold2t1w_dof = 9
    fmap_bspline = False
    fmap_demean = True
    use_syn = True
    force_syn = False
    template_out_grid = op.join(os.getenv("FSLDIR"), 
        "data", "standard", "MNI152_T1_2mm.nii.gz")
    cifti_output = False
    use_aroma = True
    ignore_aroma_err = False
    aroma_melodic_dim = None

    subject_wf = pe.Workflow(name = subject)

    inputnode = pe.Node(niu.IdentityInterface(fields = 
            ["t1w", "t2w", "flair", "subject_id", "subjects_dir"]),
        name = "inputnode")

    if not "T1w" in value0:
        return subject_wf            
        
    inputnode.inputs.t1w = value0["T1w"]  
    
    has_func = False
    for name, value1 in value0.items():
        if name not in anat_field_names:
            has_func = True
    if not has_func:
        return subject_wf
    
    anat_preproc_wf = init_anat_preproc_wf(name = "T1w",
        skull_strip_template = skull_strip_template,
        output_spaces = output_spaces,
        template = template,
        debug = debug,
        longitudinal = longitudinal,
        omp_nthreads = omp_nthreads,
        freesurfer = freesurfer,
        hires = hires,
        reportlets_dir = fmriprep_reportlets_dir,
        output_dir = fmriprep_output_dir,
        num_t1w = 1)
                            
    subject_wf.connect([
        (inputnode, anat_preproc_wf, [
            ("t1w", "inputnode.t1w"),
            ("t2w", "inputnode.t2w"),
            ("flair", "inputnode.flair"),
            ("subjects_dir", "inputnode.subjects_dir"),
            ("subject_id", "inputnode.subject_id")
        ])
    ])
    
    for name, value1 in value0.items():
        if name not in anat_field_names:
            def add(wf, inputnode, bold_file, run = None):
                layout = FakeBIDSLayout(bold_file, data["metadata"][name])
                
                func_preproc_wf = init_func_preproc_wf(
                    bold_file = bold_file,
                    layout = layout,
                    ignore = ignore,
                    freesurfer = freesurfer,
                    use_bbr = use_bbr,
                    t2s_coreg = t2s_coreg,
                    bold2t1w_dof = bold2t1w_dof,
                    reportlets_dir = fmriprep_reportlets_dir,
                    output_spaces = output_spaces,
                    template = template,
                    medial_surface_nan = medial_surface_nan,
                    cifti_output = cifti_output,
                    output_dir = fmriprep_output_dir,
                    omp_nthreads = omp_nthreads,
                    low_mem = low_mem,
                    fmap_bspline = fmap_bspline,
                    fmap_demean = fmap_demean,
                    use_syn = use_syn,
                    force_syn = force_syn,
                    debug = debug,
                    template_out_grid = template_out_grid,
                    use_aroma = use_aroma,
                    aroma_melodic_dim = aroma_melodic_dim,
                    ignore_aroma_err = ignore_aroma_err)
                
                for node in subject_wf._get_all_nodes():
                    if type(node._interface) is fsl.SUSAN:
                        node._interface.inputs.fwhm = float(data["metadata"]["SmoothingFWHM"])
                
                repetition_time = data["metadata"][name]["RepetitionTime"]
                
                temporalfilter_wf = init_temporalfilter_wf(
                    data["metadata"]["TemporalFilter"], 
                    repetition_time,
                    name = "temporalfilter_wf"
                )
                
                maskpreproc = pe.Node(
                    interface = fsl.ApplyMask(),
                    name = "mask_preproc"
                )
                
                ds_preproc = pe.Node(
                    DerivativesDataSink(
                        base_directory = output_dir, 
                        source_file = bold_file,
                        suffix = "preproc"),
                name = "ds_preproc", run_without_submitting = True)
                
                wf.connect([
                    (inputnode, func_preproc_wf, [
                        (f, "inputnode.%s" % f) 
                            for f in _func_inputnode_fields
                    ]),
                    (func_preproc_wf, temporalfilter_wf, [
                        ("outputnode.nonaggr_denoised_file", "inputnode.bold_file")
                    ]),
                    (temporalfilter_wf, maskpreproc, [
                        ("outputnode.filtered_file", "in_file")
                    ]),
                    (func_preproc_wf, maskpreproc, [
                        ("outputnode.bold_mask_mni", "mask_file")
                    ]),
                    (maskpreproc, ds_preproc, [
                        ("out_file", "in_file")
                    ])
                ])
                
                conditions = None
                if "Conditions" in data["metadata"][name]:
                    conditions = lookup(data["metadata"][name]["Conditions"],
                        subject_id = subject, run_id = run)    
                if not (conditions is None or len(conditions) == 0):
                    contrasts = data["metadata"][name]["Contrasts"]
                    
                    firstlevel_wf, connames = init_firstlevel_wf(
                        conditions, 
                        contrasts, 
                        repetition_time,
                        data["metadata"][name]["UseMovPar"],
                        name = "firstlevel_wf"
                    )
                    
                    ds_copes = pe.Node(
                        DerivativesDataSink(
                            base_directory = output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_cope"),
                    name = "ds_copes", run_without_submitting = True)
                    ds_copes.inputs.extra_values = connames
                    
                    ds_varcopes = pe.Node(
                        DerivativesDataSink(
                            base_directory = output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_varcope"),
                    name = "ds_varcopes", run_without_submitting = True)
                    ds_varcopes.inputs.extra_values = connames
                    
                    ds_zstats = pe.Node(
                        DerivativesDataSink(
                            base_directory = output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_zstat"),
                    name = "ds_zstat", run_without_submitting = True)
                    ds_zstats.inputs.extra_values = connames
                    
                    ds_dof_file = pe.Node(
                        DerivativesDataSink(
                            base_directory = output_dir, 
                            source_file = bold_file,
                            suffix = "dof.txt"),
                    name = "ds_dof_file", run_without_submitting = True)
                    
                    wf.connect([
                        (func_preproc_wf, firstlevel_wf, [
                            ("outputnode.bold_mask_mni", "inputnode.mask_file"),
                            ("bold_hmc_wf.outputnode.movpar_file", "inputnode.confounds_file")
                        ]),
                        (temporalfilter_wf, firstlevel_wf, [
                            ("outputnode.filtered_file", "inputnode.bold_file")
                        ]),
                        (firstlevel_wf, ds_copes, [
                            ("outputnode.copes", "in_file")
                        ]),
                        (firstlevel_wf, ds_varcopes, [
                            ("outputnode.varcopes", "in_file")
                        ]),
                        (firstlevel_wf, ds_zstats, [
                            ("outputnode.zstats", "in_file")
                        ]),
                        (firstlevel_wf, ds_dof_file, [
                            ("outputnode.dof_file", "in_file")
                        ])
                    ])
                if "ConnectivitySeeds" in data["metadata"][name]:
                    firstlevel_wf, seednames = init_seed_connectivity_wf(
                        data["metadata"][name]["ConnectivitySeeds"],
                        name = "firstlevel_wf"
                    )
                    
                    ds_copes = pe.Node(
                        DerivativesDataSink(
                            base_directory = output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_cope"),
                    name = "ds_copes_%s" % name, run_without_submitting = True)
                    ds_copes.inputs.extra_values = seednames
                    
                    ds_varcopes = pe.Node(
                        DerivativesDataSink(
                            base_directory = output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_varcope"),
                    name = "ds_varcopes_%s" % name, run_without_submitting = True)
                    ds_varcopes.inputs.extra_values = seednames
                    
                    ds_zstats = pe.Node(
                        DerivativesDataSink(
                            base_directory = output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_zstat"),
                    name = "ds_zstat_%s" % name, run_without_submitting = True)
                    ds_zstats.inputs.extra_values = seednames
                    
                    wf.connect([
                        (func_preproc_wf, firstlevel_wf, [
                            ("outputnode.bold_mask_mni", "inputnode.mask_file")
                        ]),
                        (temporalfilter_wf, firstlevel_wf, [
                            ("outputnode.filtered_file", "inputnode.bold_file")
                        ]),
                        (firstlevel_wf, ds_copes, [
                            ("outputnode.copes", "in_file")
                        ]),
                        (firstlevel_wf, ds_varcopes, [
                            ("outputnode.varcopes", "in_file")
                        ]),
                        (firstlevel_wf, ds_zstats, [
                            ("outputnode.zstats", "in_file")
                        ])
                    ])
            
            scan_wf = pe.Workflow(name = name)
            
            inputnode = pe.Node(niu.IdentityInterface(
                fields = _func_inputnode_fields,
            ), name = "inputnode")
            scan_wf.add_nodes((inputnode,))
                
            subject_wf.connect([
                (anat_preproc_wf, scan_wf, [
                    ("outputnode.%s" % f, "inputnode.%s" % f) 
                        for f in _func_inputnode_fields
                ])
            ])
            
            if isinstance(value1, dict):
                for run, bold_file in value1.items():
                    run_wf = pe.Workflow(name = run)
                    
                    run_inputnode = pe.Node(niu.IdentityInterface(
                        fields = _func_inputnode_fields,
                    ), name = "inputnode")
                    run_wf.add_nodes((inputnode,))
                        
                    scan_wf.connect([
                        (inputnode, run_wf, [
                            (f, "inputnode.%s" % f) 
                                for f in _func_inputnode_fields
                        ])
                    ])
                    
                    add(run_wf, run_inputnode, bold_file, run = run)
            else:
                add(scan_wf, inputnode, value1)

    subject_wf = patch_wf(subject_wf, 
        images, fmriprep_reportlets_dir, fmriprep_output_dir)

    return subject_wf
