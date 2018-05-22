import json
import os
from os import path as op
from copy import deepcopy

from nipype.interfaces.base import Bunch

import nipype.interfaces.fsl as fsl
import nipype.algorithms.modelgen as model

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

def transpose(d):
    out = dict()
    for key0, value0 in d.items():
        for key1, value1 in value0.items():
            if key1 not in out:
                out[key1] = dict()
            while isinstance(value1, dict) and len(value1) == 1 and "" in value1:
                value1 = value1[""]
            out[key1][key0] = value1
    return out

def init_workflow(workdir):
    fp = op.join(workdir, "pipeline.json")
    
    data = None
    with open(fp, "r") as f:
        data = json.load(f)
        
    name = "workflow"
    
    workflow = pe.Workflow(name = name)
    
    #
    # fmriprep
    #
    
    reportlets_dir = op.join(workdir, "reportlets")
    output_dir = op.join(workdir, "derivatives")
    real_output_dir = op.join(workdir, "output")
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
    use_aroma = True
    ignore_aroma_err = False
    
    images = transpose(data["images"])
    anat_field_names = ["T1w", "T2w", "FLAIR"]
    
    for subject, value0 in images.items():
        subject_wf = pe.Workflow(name = "%s_wf" % subject)
        
        inputnode = pe.Node(niu.IdentityInterface(fields = 
                ["t1w", "t2w", "flair", "subject_id", "subjects_dir"]),
            name = "inputnode")
        
        if "T1w" in value0:
            inputnode.inputs.t1w = value0["T1w"]  
        if "T2w" in value0:          
            inputnode.inputs.t2w = value0["T2w"]  
        if "FLAIR" in value0:                      
            inputnode.inputs.flair = value0["FLAIR"]            

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
                def add(bold_file):
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
                        ignore_aroma_err = ignore_aroma_err)
                        
                    for node in subject_wf._get_all_nodes():
                        if type(node._interface) is fsl.SUSAN:
                            node._interface.inputs.fwhm = float(data["metadata"]["SmoothingFWHM"])
                    
                    temporalfilter_wf = init_temporalfilter_wf(
                        data["metadata"]["TemporalFilter"], 
                        data["metadata"][name]["RepetitionTime"]
                    )
                    
                    ds_temporalfilter = pe.Node(
                        DerivativesDataSink(
                            base_directory = real_output_dir, 
                            source_file = bold_file,
                            suffix = "preproc"),
                    name = "ds_temporalfilter", run_without_submitting = True)
                    
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
                    
                if isinstance(value1, dict):
                    for run, bold_file in value1.items():
                        add(bold_file)
                else:
                    add(value1)
        
        for node in subject_wf._get_all_nodes():
            if type(node._interface) is DerivativesDataSink:
                base_directory = node._interface.inputs.base_directory
                in_file = node._interface.inputs.in_file
                source_file = node._interface.inputs.source_file
                suffix = node._interface.inputs.suffix
                extra_values = node._interface.inputs.extra_values
                node._interface = FakeDerivativesDataSink(images, 
                    base_directory = base_directory,
                    source_file = source_file,
                    in_file = in_file,
                    suffix = suffix,
                    extra_values = extra_values)
        
        for node in subject_wf._get_all_nodes():
            node.config = deepcopy(subject_wf.config)
    
        workflow.add_nodes([subject_wf])
    
    return workflow             
    
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
        interface = 
            fsl.BinaryMaths(operation = "add"), 
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
    
          
# def init_modelfit_workflow():
#     modelfit = pe.Workflow(name = "modelfit")
# 
#     modelspec = pe.Node(interface = model.SpecifyModel(), name = "modelspec")
#     level1design = pe.Node(interface = fsl.Level1Design(), name = "level1design")
# 
#     modelgen = pe.MapNode(
#         interface = fsl.FEATModel(),
#         name = "modelgen",
#         iterfield = ["fsf_file", "ev_files"])
# 
#     modelestimate = pe.MapNode(
#         interface=fsl.FILMGLS(smooth_autocorr=True, mask_size=5, threshold=1000),
#         name="modelestimate",
#         iterfield=["design_file", "in_file"])
# 
#     conestimate = pe.MapNode(
#     interface=fsl.ContrastMgr(),
#     name="conestimate",
#     iterfield=[
#         "tcon_file", "param_estimates", "sigmasquareds", "corrections",
#         "dof_file"
#     ])
# 
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