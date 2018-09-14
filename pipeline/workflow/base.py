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

from .func import (
    init_temporalfilter_wf,
    init_tsnr_wf
)
from .rest import (
    init_seedconnectivity_wf,
    init_dualregression_wf
)
from .task import init_firstlevel_wf
from .stats import init_higherlevel_wf

from .qualitycheck import get_qualitycheck_exclude

from ..utils import (
    transpose,
    lookup,
    flatten
)


bids_dir = "."
longitudinal = False
t2s_coreg = False
omp_nthreads = 1
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

_func_inputnode_fields = ['t1_preproc', 't1_brain', 't1_mask', 't1_seg', 
    't1_tpms', 't1_aseg', 't1_aparc', 
    't1_2_mni_forward_transform', 't1_2_mni_reverse_transform', 
    'subjects_dir', 'subject_id',
    't1_2_fsnative_forward_transform', 't1_2_fsnative_reverse_transform']


def init_workflow(workdir):
    workflow_file = op.join(workdir, "workflow.pklz")

    fp = op.join(workdir, "pipeline.json")

    data = None
    with open(fp, "r") as f:
        data = json.load(f)
        
    name = "nipype"    
    workflow = pe.Workflow(name = name, base_dir = workdir)

    images = transpose(data["images"])
        
    result = Pool().map(
        partial(init_subject_wf, workdir = workdir, images = images, data = data), 
        list(images.items())
    )
    subjects, subject_wfs, outnameslists = zip(*result)
    workflow.add_nodes(subject_wfs)
    
    outnamessets = {}
    for outnameslist in outnameslists:
        for k, v in outnameslist.items():
            if k not in outnamessets:
                outnamessets[k] = set()
            outnamessets[k].update(v)
    
    exclude = get_qualitycheck_exclude(workdir)
    
    stats_dir = op.join(workdir, "stats")
    
    for task, outnamesset in outnamessets.items():
        for outname in outnamesset:
            higherlevel_wf = init_higherlevel_wf(run_mode = "flame1", 
                name = "%s_%s_higherlevel" % (task, outname))
        
            mergecopes = pe.Node(
                interface = niu.Merge(len(subject_wfs)),
                name = "%s_%s_mergecopes" % (task, outname))
            mergevarcopes = pe.Node(
                interface = niu.Merge(len(subject_wfs)),
                name = "%s_%s_mergevarcopes" % (task, outname))
            mergedoffiles = pe.Node(
                interface = niu.Merge(len(subject_wfs)),
                name = "%s_%s_mergedoffiles" % (task, outname))
            
            for i, (subject, wf) in enumerate(zip(subjects, subject_wfs)):
                excludethis = False
                if subject in exclude:
                    if task in exclude[subject]:
                        excludethis = exclude[subject][task]
                if not excludethis:
                    nodename = "task-%s.outputnode" % task
                    outputnode = [
                        node for node in wf._graph.nodes()
                        if str(node).endswith('.' + nodename)
                    ]
                    if len(outputnode) > 0:
                        outputnode = outputnode[0]
                        workflow.connect(outputnode, "%s_cope" % outname, mergecopes, "in%i" % (i+1))
                        workflow.connect(outputnode, "%s_varcope" % outname, mergevarcopes, "in%i" % (i+1))
                        workflow.connect(outputnode, "%s_dof_file" % outname, mergedoffiles, "in%i" % (i+1))
        
            ds_cope = pe.Node(
                DerivativesDataSink(
                    base_directory = op.join(stats_dir, task), 
                    source_file = "",
                    suffix = "%s_cope" % task),
                name = "ds_%s_%s_cope" % (task, outname), run_without_submitting = True)
            ds_varcope = pe.Node(
                DerivativesDataSink(
                    base_directory = stats_dir, 
                    source_file = "",
                    suffix = "%s_cope" % task),
                name = "ds_%s_%s_varcope" % (task, outname), run_without_submitting = True)
            ds_zstat = pe.Node(
                DerivativesDataSink(
                    base_directory = stats_dir, 
                    source_file = "",
                    suffix = "%s_varcope" % task),
                name = "ds_%s_%s_zstat" % (task, outname), run_without_submitting = True)
            ds_dof_file = pe.Node(
                DerivativesDataSink(
                    base_directory = stats_dir, 
                    source_file = "",
                    suffix = "%s_dof" % task),
                name = "ds_%s_%s_dof_file" % (task, outname), run_without_submitting = True)
    
            workflow.connect([
                (mergecopes, higherlevel_wf, [
                    ("out", "inputnode.copes")
                ]),
                (mergevarcopes, higherlevel_wf, [
                    ("out", "inputnode.varcopes")
                ]),
                (mergedoffiles, higherlevel_wf, [
                    ("out", "inputnode.dof_files")
                ]),
                
                (higherlevel_wf, ds_cope, [
                    ("outputnode.cope", "in_file")
                ]),
                (higherlevel_wf, ds_varcope, [
                    ("outputnode.varcope", "in_file")
                ]),
                (higherlevel_wf, ds_zstat, [
                    ("outputnode.zstat", "in_file")
                ]),
                (higherlevel_wf, ds_dof_file, [
                    ("outputnode.dof_file", "in_file")
                ])
            ])
        
    return workflow  

    
def init_subject_wf(item, workdir, images, data):
    subject, value0 = item
    
    anat_field_names = ["T1w", "T2w", "FLAIR"]

    fmriprep_output_dir = op.join(workdir, "fmriprep_output")
    fmriprep_reportlets_dir = op.join(workdir, "fmriprep_reportlets")
    output_dir = op.join(workdir, "intermediates")

    subject_wf = pe.Workflow(name = "sub-" + subject)

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
    
    outnames = {}
    
    for i, (name, value1) in enumerate(value0.items()):
        if name not in anat_field_names:
            task_wf = pe.Workflow(name = "task-" + name)
            
            inputnode = pe.Node(niu.IdentityInterface(
                fields = _func_inputnode_fields,
            ), name = "inputnode")
            task_wf.add_nodes((inputnode,))
                
            subject_wf.connect([
                (anat_preproc_wf, task_wf, [
                    ("outputnode.%s" % f, "inputnode.%s" % f) 
                        for f in _func_inputnode_fields
                ])
            ])
            
            metadata = data["metadata"][name]
            metadata["SmoothingFWHM"] = data["metadata"]["SmoothingFWHM"]
            metadata["TemporalFilter"] = data["metadata"]["TemporalFilter"]
            if "UseMovPar" not in metadata:
                metadata["UseMovPar"] = False
            
            if isinstance(value1, dict):
                run_wfs = []
                outnamesset = set()
                
                for run, bold_file in value1.items():
                    run_wf = pe.Workflow(name = "run-" + run)
                    run_wfs.append(run_wf)
                    
                    run_inputnode = pe.Node(niu.IdentityInterface(
                        fields = _func_inputnode_fields,
                    ), name = "inputnode")
                    run_wf.add_nodes((inputnode,))
                        
                    task_wf.connect([
                        (inputnode, run_wf, [
                            (f, "inputnode.%s" % f) 
                                for f in _func_inputnode_fields
                        ])
                    ])
                    run_outnames = create_func_wf(run_wf, run_inputnode, bold_file, metadata, 
                        fmriprep_reportlets_dir, fmriprep_output_dir, output_dir, run = run)
                    outnamesset.update(run_outnames)
                
                outnames[name] = outnamesset
                
                outputnode = pe.Node(niu.IdentityInterface(
                    fields = sum([["%s_cope" % outname, 
                            "%s_varcope" % outname, "%s_dof_file" % outname] 
                        for outname in outnames[name]], [])), 
                    name = "outputnode"
                )
            
                for outname in outnames[name]:
                    mergecopes = pe.Node(
                        interface = niu.Merge(len(run_wfs)),
                        name = "%s_mergecopes" % outname)
                    mergevarcopes = pe.Node(
                        interface = niu.Merge(len(run_wfs)),
                        name = "%s_mergevarcopes" % outname)
                    mergedoffiles = pe.Node(
                        interface = niu.Merge(len(run_wfs)),
                        name = "%s_mergedoffiles" % outname)
                    
                    for i, wf in run_wfs:
                        task_wf.connect(wf, "outputnode.%s_cope" % outname, mergecopes, "in%i" % (i+1))
                        task_wf.connect(wf, "outputnode.%s_varcope" % outname, mergevarcopes, "in%i" % (i+1))
                        task_wf.connect(wf, "outputnode.%s_dof_file" % outname, mergedoffiles, "in%i" % (i+1))
                
                    fe_wf = init_higherlevel_wf(run_mode = "fe", 
                        name = "%s_fe" % outname)
                        
                    task_wf.connect([
                        (mergecopes, fe_wf, [
                            ("out", "inputnode.copes")
                        ]),
                        (mergevarcopes, fe_wf, [
                            ("out", "inputnode.varcopes")
                        ]),
                        (mergedoffiles, fe_wf, [
                            ("out", "inputnode.dof_files")
                        ]),
                        
                        (fe_wf, outputnode, [
                            ("outputnode.cope", "%s_cope" % outname),
                            ("outputnode.varcope", "%s_varcope" % outname),
                            ("outputnode.dof_file", "%s_dof_file" % outname)
                        ])
                    ])
            else:
                outnames[name] = create_func_wf(task_wf, inputnode, value1, metadata,
                    fmriprep_reportlets_dir, fmriprep_output_dir, output_dir)
            
    subject_wf = patch_wf(subject_wf, 
        images, output_dir, fmriprep_reportlets_dir, fmriprep_output_dir)

    return subject, subject_wf, outnames

def create_ds(wf, firstlevel_wf, outnames,
        func_preproc_wf, temporalfilter_wf,
        bold_file, output_dir, name = "firstlevel"):
        
    ds_dof_file = pe.Node(
        DerivativesDataSink(
            base_directory = output_dir, 
            source_file = bold_file,
            suffix = "dof"),
        name = "ds_%s_dof_file" % name, run_without_submitting = True)

    wf.connect([
        (func_preproc_wf, firstlevel_wf, [
            ("outputnode.bold_mask_mni", "inputnode.mask_file"),
            ("bold_hmc_wf.outputnode.movpar_file", "inputnode.confounds_file")
        ]),
        (temporalfilter_wf, firstlevel_wf, [
            ("outputnode.filtered_file", "inputnode.bold_file")
        ]),
        (firstlevel_wf, ds_dof_file, [
            ("outputnode.dof_file", "in_file")
        ])
    ])  

    for outname in outnames:
        ds_cope = pe.Node(
            DerivativesDataSink(
                base_directory = output_dir, 
                source_file = bold_file,
                suffix = "%s_cope" % outname),
            name = "ds_%s_%s_cope" % (name, outname), run_without_submitting = True)
        ds_varcope = pe.Node(
            DerivativesDataSink(
                base_directory = output_dir, 
                source_file = bold_file,
                suffix = "%s_varcope" % outname),
            name = "ds_%s_%s_varcope" % (name, outname), run_without_submitting = True)
        ds_zstat = pe.Node(
            DerivativesDataSink(
                base_directory = output_dir, 
                source_file = bold_file,
                suffix = "%s_zstat" % outname),
            name = "ds_%s_%s_zstat" % (name, outname), run_without_submitting = True)
        
        wf.connect([
            (firstlevel_wf, ds_cope, [
                ("outputnode.%s_cope" % outname, "in_file")
            ]),
            (firstlevel_wf, ds_varcope, [
                ("outputnode.%s_varcope" % outname, "in_file")
            ]),
            (firstlevel_wf, ds_zstat, [
                ("outputnode.%s_zstat" % outname, "in_file")
            ]),
        ])


def create_func_wf(wf, inputnode, bold_file, metadata,
        fmriprep_reportlets_dir, fmriprep_output_dir, output_dir, run = None):
    while isinstance(bold_file, dict):
        bold_file = next(iter(bold_file.values()))
    
    layout = FakeBIDSLayout(bold_file, metadata)
    
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
    
    for node in func_preproc_wf._get_all_nodes():
        if type(node._interface) is fsl.SUSAN:
            node._interface.inputs.fwhm = float(metadata["SmoothingFWHM"])
    
    repetition_time = metadata["RepetitionTime"]
    
    temporalfilter_wf = init_temporalfilter_wf(
        metadata["TemporalFilter"], 
        repetition_time
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
    
    tsnr_wf = init_tsnr_wf()
    ds_tsnr = pe.Node(
        DerivativesDataSink(
            base_directory = fmriprep_reportlets_dir, 
            source_file = bold_file,
            suffix = "tsnr"),
    name = "ds_tsnr", run_without_submitting = True)
    
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
        ]),
        (temporalfilter_wf, tsnr_wf, [
            ("outputnode.filtered_file", "inputnode.bold_file")
        ]),
        (tsnr_wf, ds_tsnr, [
            ("outputnode.report_file", "in_file")
        ])
    ])
    
    conditions = None
    if "Conditions" in metadata:
        conditions = lookup(metadata["Conditions"],
            subject_id = subject, run_id = run)
    
    wfbywf = {}
    outnamesbywf = {}
      
    if not (conditions is None or len(conditions) == 0):
        contrasts = metadata["Contrasts"]
        firstlevel_wf, connames = init_firstlevel_wf(
            conditions, 
            contrasts, 
            repetition_time,
            metadata["UseMovPar"],
            name = "firstlevel_wf"
        )
        create_ds(wf, firstlevel_wf, connames, func_preproc_wf, temporalfilter_wf, 
            bold_file, output_dir, name = "firstlevel")
        wfbywf["firstlevel_wf"] = firstlevel_wf
        outnamesbywf["firstlevel_wf"] = connames
    if "ConnectivitySeeds" in metadata:
        firstlevel_wf, seednames = init_seedconnectivity_wf(
            metadata["ConnectivitySeeds"],
            metadata["UseMovPar"],
            name = "seedconnectivity_wf"
        )
        create_ds(wf, firstlevel_wf, seednames, func_preproc_wf, temporalfilter_wf, 
            bold_file, output_dir, name = "seedconnectivity")
        wfbywf["seedconnectivity_wf"] = firstlevel_wf
        outnamesbywf["seedconnectivity_wf"] = seednames
    if "ICAMaps" in metadata:
        firstlevel_wf, componentnames = init_dualregression_wf(
            metadata["ICAMaps"],
            metadata["UseMovPar"],
            name = "dualregression_wf"
        )
        create_ds(wf, firstlevel_wf, componentnames, func_preproc_wf, temporalfilter_wf, 
            bold_file, output_dir, name = "dualregression")
        wfbywf["dualregression_wf"] = firstlevel_wf
        outnamesbywf["dualregression_wf"] = componentnames
    
    outputnode = pe.Node(
        interface = niu.IdentityInterface(
            fields = flatten([[["%s_cope" % w, 
                "%s_varcope" % w, "%s_dof_file" % w] for w in v] for v in outnamesbywf.values()])
        ),
        name = "outputnode")

    for k, v in outnamesbywf.items():
        for w in v:
            wf.connect(wfbywf[k], "outputnode.%s_cope" % w, outputnode, "%s_cope" % w)
            wf.connect(wfbywf[k], "outputnode.%s_varcope" % w, outputnode, "%s_varcope" % w)
            wf.connect(wfbywf[k], "outputnode.dof_file", outputnode, "%s_dof_file" % w)
    
    outnames = sum(outnamesbywf.values(), [])
    return outnames
    
    