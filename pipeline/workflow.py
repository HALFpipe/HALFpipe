import json
import os
from os import path as op
from copy import deepcopy

import gzip
import pickle

from functools import partial
from multiprocessing import Pool

from niworkflows.nipype.interfaces.base import Bunch

import niworkflows.nipype.interfaces.fsl as fsl
import niworkflows.nipype.algorithms.modelgen as model
from niworkflows.nipype.interfaces.base import Bunch

from fmriprep.interfaces.bids import DerivativesDataSink

from niworkflows.nipype.pipeline import engine as pe
from niworkflows.nipype.interfaces import utility as niu
from niworkflows.nipype.interfaces import fsl

from fmriprep.workflows.anatomical import init_anat_preproc_wf
from fmriprep.workflows.bold import init_func_preproc_wf

from mriqc.workflows.anatomical import anat_qc_workflow
from mriqc.workflows.functional import fmri_qc_workflow

from .fake import (
    FakeBIDSLayout,
    FakeDerivativesDataSink
)

from .utils import (
    transpose,
    lookup
)

def init_workflow(workdir):
    workflow_file = op.join(workdir, "workflow.pklz")
    
    workflow = None
    if op.isfile(workflow_file):
        with gzip.open(workflow_file, "rb") as f:
            workflow = pickle.load(f)
    else:
        fp = op.join(workdir, "pipeline.json")
        
        data = None
        with open(fp, "r") as f:
            data = json.load(f)
            
        name = "intermediates"
        workflow = pe.Workflow(name = name, base_dir = workdir)
        
        images = transpose(data["images"])
        
        # for subject, value0 in images.items():
        #     subject_wf = init_subject_wf((subject, value0), workdir, images, data)
        #     workflow.add_nodes([subject_wf])
            
        subject_wfs = Pool().map(
            partial(init_subject_wf, workdir = workdir, images = images, data = data), 
            list(images.items())
        )
        workflow.add_nodes(subject_wfs)
        
        # import pdb; pdb.set_trace()
        
        with gzip.open(workflow_file, "wb") as f:
            pickle.dump(workflow, f)
    
    return workflow             

def init_subject_wf(item, workdir, images, data):
    subject, value0 = item
    
    anat_field_names = ["T1w", "T2w", "FLAIR"]
    
    #
    # fmriprep
    #

    output_dir = op.join(workdir, "fmriprep_derivatives")
    reportlets_dir = output_dir
    real_output_dir = op.join(workdir, "results")
    bids_dir = "."

    subject_id = "test"
    task_id = ""
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

    subject_wf = pe.Workflow(name = "%s_wf" % subject)

    inputnode = pe.Node(niu.IdentityInterface(fields = 
            ["t1w", "t2w", "flair", "subject_id", "subjects_dir"]),
        name = "inputnode")

    if "T1w" in value0:
        inputnode.inputs.t1w = value0["T1w"]  
    else:
        return subject_wf

    if "T2w" in value0:          
        inputnode.inputs.t2w = value0["T2w"]  
    if "FLAIR" in value0:                      
        inputnode.inputs.flair = value0["FLAIR"]            
    
    has_func = False
    for name, value1 in value0.items():
        if name not in anat_field_names:
            has_func = True
    if not has_func:
        return subject_wf
    
    anat_preproc_wf = init_anat_preproc_wf(name = "anat_preproc_wf",
        skull_strip_template = skull_strip_template,
        output_spaces = output_spaces,
        template = template,
        debug = debug,
        longitudinal = longitudinal,
        omp_nthreads = omp_nthreads,
        freesurfer = freesurfer,
        hires = hires,
        reportlets_dir = reportlets_dir,
        output_dir = output_dir,
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
            def add(bold_file, run = None):
                layout = FakeBIDSLayout(bold_file, data["metadata"][name])
                
                func_preproc_wf = init_func_preproc_wf(
                    bold_file = bold_file,
                    layout = layout,
                    ignore = ignore,
                    freesurfer = freesurfer,
                    use_bbr = use_bbr,
                    t2s_coreg = t2s_coreg,
                    bold2t1w_dof = bold2t1w_dof,
                    reportlets_dir = reportlets_dir,
                    output_spaces = output_spaces,
                    template = template,
                    medial_surface_nan = medial_surface_nan,
                    cifti_output = cifti_output,
                    output_dir = output_dir,
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
                    name = "temporalfilter_wf_%s" % name
                )
                
                ds_temporalfilter = pe.Node(
                    DerivativesDataSink(
                        base_directory = real_output_dir, 
                        source_file = bold_file,
                        suffix = "preproc"),
                name = "ds_temporalfilter_%s" % name, run_without_submitting = True)
                
                subject_wf.connect([
                    (anat_preproc_wf, func_preproc_wf, [
                        ("outputnode.t1_preproc", "inputnode.t1_preproc"),
                        ("outputnode.t1_brain", "inputnode.t1_brain"),
                        ("outputnode.t1_mask", "inputnode.t1_mask"),
                        ("outputnode.t1_seg", "inputnode.t1_seg"),
                        ("outputnode.t1_aseg", "inputnode.t1_aseg"),
                        ("outputnode.t1_aparc", "inputnode.t1_aparc"),
                        ("outputnode.t1_tpms", "inputnode.t1_tpms"),
                        ("outputnode.t1_2_mni_forward_transform", "inputnode.t1_2_mni_forward_transform"),
                        ("outputnode.t1_2_mni_reverse_transform", "inputnode.t1_2_mni_reverse_transform"),
                        # Undefined if --no-freesurfer, but this is safe
                        ("outputnode.subjects_dir", "inputnode.subjects_dir"),
                        ("outputnode.subject_id", "inputnode.subject_id"),
                        ("outputnode.t1_2_fsnative_forward_transform", "inputnode.t1_2_fsnative_forward_transform"),
                        ("outputnode.t1_2_fsnative_reverse_transform", "inputnode.t1_2_fsnative_reverse_transform")
                    ]),
                    (func_preproc_wf, temporalfilter_wf, [
                        ("outputnode.nonaggr_denoised_file", "inputnode.bold_file")
                    ]),
                    (temporalfilter_wf, ds_temporalfilter, [
                        ("outputnode.filtered_file", "in_file")
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
                        name = "firstlevel_wf_%s" % name
                    )
                    
                    ds_copes = pe.Node(
                        DerivativesDataSink(
                            base_directory = real_output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_cope"),
                    name = "ds_copes_%s" % name, run_without_submitting = True)
                    ds_copes.inputs.extra_values = connames
                    
                    ds_varcopes = pe.Node(
                        DerivativesDataSink(
                            base_directory = real_output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_varcope"),
                    name = "ds_varcopes_%s" % name, run_without_submitting = True)
                    ds_varcopes.inputs.extra_values = connames
                    
                    ds_dof_file = pe.Node(
                        DerivativesDataSink(
                            base_directory = real_output_dir, 
                            source_file = bold_file,
                            suffix = "dof.txt"),
                    name = "ds_dof_file_%s" % name, run_without_submitting = True)
                    
                    subject_wf.connect([
                        (temporalfilter_wf, firstlevel_wf, [
                            ("outputnode.filtered_file", "inputnode.bold_file")
                        ]),
                        (firstlevel_wf, ds_copes, [
                            ("outputnode.copes", "in_file")
                        ]),
                        (firstlevel_wf, ds_varcopes, [
                            ("outputnode.varcopes", "in_file")
                        ]),
                        (firstlevel_wf, ds_dof_file, [
                            ("outputnode.dof_file", "in_file")
                        ])
                    ])
                if "ConnectivitySeeds" in data["metadata"][name]:
                    firstlevel_wf, seednames = init_firstlevel_seed_connectivity_wf(
                        data["metadata"][name]["ConnectivitySeeds"],
                        name = "firstlevel_wf_%s" % name
                    )
                    
                    ds_copes = pe.Node(
                        DerivativesDataSink(
                            base_directory = real_output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_cope"),
                    name = "ds_copes_%s" % name, run_without_submitting = True)
                    ds_copes.inputs.extra_values = seednames
                    
                    ds_varcopes = pe.Node(
                        DerivativesDataSink(
                            base_directory = real_output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_varcope"),
                    name = "ds_varcopes_%s" % name, run_without_submitting = True)
                    ds_varcopes.inputs.extra_values = seednames
                    
                    ds_zstat = pe.Node(
                        DerivativesDataSink(
                            base_directory = real_output_dir, 
                            source_file = bold_file,
                            suffix = "{extra_value}_zstat"),
                    name = "ds_zstat_%s" % name, run_without_submitting = True)
                    
                    subject_wf.connect([
                        (temporalfilter_wf, firstlevel_wf, [
                            ("outputnode.filtered_file", "inputnode.bold_file")
                        ]),
                        (firstlevel_wf, ds_copes, [
                            ("outputnode.copes", "in_file")
                        ]),
                        (firstlevel_wf, ds_varcopes, [
                            ("outputnode.varcopes", "in_file")
                        ]),
                        (firstlevel_wf, ds_zstat, [
                            ("outputnode.zstats", "in_file")
                        ])
                    ])
                    
                
            if isinstance(value1, dict):
                for run, bold_file in value1.items():
                    add(bold_file, run = run)
            else:
                add(value1)

    # Patch workflows

    def _get_all_workflows(wf):
        workflows = [wf]
        for node in wf._graph.nodes():
            if isinstance(node, pe.Workflow):
                workflows.extend(_get_all_workflows(node))
        return workflows
                    
    workflows = _get_all_workflows(subject_wf)       

    for wf in workflows:
        for _, _, d in wf._graph.edges(data = True):
            for i, (src, dest) in enumerate(d["connect"]):
                if isinstance(src, tuple) and len(src) > 1:
                    if "fix_multi_T1w_source_name" in src[1]:
                        d["connect"][i] = (src[0], dest)

    for node in subject_wf._get_all_nodes():
        if type(node._interface) is DerivativesDataSink:
            base_directory = node._interface.inputs.base_directory
            in_file = node._interface.inputs.in_file
            source_file = node._interface.inputs.source_file
            suffix = node._interface.inputs.suffix
            extra_values = node._interface.inputs.extra_values
            node._interface = FakeDerivativesDataSink(images, output_dir,
                base_directory = base_directory,
                source_file = source_file,
                in_file = in_file,
                suffix = suffix,
                extra_values = extra_values)
        elif type(node._interface) is niu.Function and \
            "fix_multi_T1w_source_name" in node._interface.inputs.function_str:
            node._interface.inputs.function_str = "def fix_multi_T1w_source_name(in_files):\n    if isinstance(in_files, str):\n        return in_files\n    else:\n        return in_files[0]"
                
    for node in subject_wf._get_all_nodes():
        node.config = deepcopy(subject_wf.config)

    # workflow.add_nodes([subject_wf])
    return subject_wf

def init_temporalfilter_wf(temporal_filter_width, repetition_time, name = "temporalfilter_wf"):
    workflow = pe.Workflow(name=name)
    
    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file"]), 
        name = "inputnode"
    )
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = ["filtered_file"]), 
        name = "outputnode"
    )
    
    highpass_operand = "-bptf %.10f -1" % \
        (temporal_filter_width / (2.0 * repetition_time))
    
    highpass = pe.Node(
        interface=fsl.ImageMaths(
            op_string = highpass_operand, suffix = "_tempfilt"),
        name="highpass"
    )
    
    meanfunc = pe.Node(
        interface = fsl.ImageMaths(
            op_string = "-Tmean", suffix = "_mean"),
        name = "meanfunc"
    )
    
    addmean = pe.Node(
        interface = fsl.BinaryMaths(
            operation = "add"), 
        name = "addmean"
    )
    
    workflow.connect([
        (inputnode, highpass, [
            ("bold_file", "in_file")
        ]),
        (inputnode, meanfunc, [
            ("bold_file", "in_file")
        ]),
        (highpass, addmean, [
            ("out_file", "in_file")
        ]),
        (meanfunc, addmean, [
            ("out_file", "operand_file")
        ]),
        (addmean, outputnode, [
            ("out_file", "filtered_file")
        ])
    ])
    
    return workflow

def init_firstlevel_seed_connectivity_wf(seeds, name = "firstlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file"]), 
        name = "inputnode"
    )
    
    seed_names = list(seeds.keys())
    seed_paths = [seeds[k] for k in seed_names]
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = ["names", "copes", "varcopes", "zstats"]), 
        name = "outputnode"
    )
    outputnode._interface.names = seed_names
    
    meants = pe.MapNode(
        interface = fsl.ImageMeants(),
        name = "meants",
        iterfield = ["mask"]
    )
    meants.inputs.mask = seed_paths
        
    glm = pe.MapNode(
        interface = fsl.GLM(), 
        name = "glm",
        iterfield = ["design"])
    glm.inputs.out_file = "beta.nii.gz"
    glm.inputs.out_cope = "cope.nii.gz"
    glm.inputs.out_varcb_name = "varcope.nii.gz"
    glm.inputs.out_z_name = "zstat.nii.gz"
    
    workflow.connect([
        (inputnode, meants, [
            ("bold_file", "in_file")
        ]),
        (inputnode, glm, [
            ("bold_file", "in_file")
        ]),
        (meants, glm, [
            ("out_file", "design")
        ]),
        (glm, outputnode, [
            ("out_cope", "copes"), 
            ("out_varcb", "varcopes"),
            ("out_z", "dof_file")
        ]),
    ])
    
    return workflow, seed_names

def init_firstlevel_wf(conditions, contrasts, repetition_time, name = "firstlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file"]), 
        name = "inputnode"
    )
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = ["names", "copes", "varcopes", "dof_file"]), 
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

    modelgen = pe.MapNode(
        interface = fsl.FEATModel(),
        name = "modelgen",
        iterfield = ["fsf_file", "ev_files"]
    )

    modelestimate = pe.MapNode(
        interface = fsl.FILMGLS(smooth_autocorr = True, 
            mask_size = 5, threshold = 0.000002),
        name = "modelestimate",
        iterfield=["design_file", "in_file", "tcon_file"]
    )
    
    workflow.connect([
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
        (modelgen, modelestimate, [
            ("design_file", "design_file"),
            ("con_file", "tcon_file")
        ]),
        (modelestimate, outputnode, [
            ("copes", "copes"), 
            ("varcopes", "varcopes"),
            ("dof_file", "dof_file")
        ]),
    ])
    
    return workflow, connames

# def init_secondlevel_wf(name = "secondlevel"):
    


# def init_first_level_workflow():
# 
# 
#     copemerge = pe.MapNode(
#     interface=fsl.Merge(dimension="t"),
#     iterfield=["in_files"],
#     name="copemerge")
# 
# varcopemerge = pe.MapNode(
#     interface=fsl.Merge(dimension="t"),
#     iterfield=["in_files"],
#     name="varcopemerge")
# 
#     level2model = pe.Node(interface=fsl.L2Model(), name="l2model")
# 
#     flameo = pe.MapNode(
#     interface=fsl.FLAMEO(run_mode="fe"),
#     name="flameo",
#     iterfield=["cope_file", "var_cope_file"])
# 
# fixed_fx.connect([
#     (copemerge, flameo, [("merged_file", "cope_file")]),
#     (varcopemerge, flameo, [("merged_file", "var_cope_file")]),
#     (level2model, flameo, [("design_mat", "design_file"),
#                            ("design_con", "t_con_file"), ("design_grp",
#                                                           "cov_split_file")]),
# ]
# 
# modelfit.connect([
#     (modelspec, level1design, [("session_info", "session_info")]),
#     (level1design, modelgen, [("fsf_files", "fsf_file"), ("ev_files",
#                                                           "ev_files")]),
#     (modelgen, modelestimate, [("design_file", "design_file")]),
#     (modelgen, conestimate, [("con_file", "tcon_file")]),
#     (modelestimate, conestimate,
#      [("param_estimates", "param_estimates"), ("sigmasquareds",
#                                                "sigmasquareds"),
#       ("corrections", "corrections"), ("dof_file", "dof_file")]),
# ])