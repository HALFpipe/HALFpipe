# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from fmriprep.interfaces.bids import _splitext

from ..interface import Dof

import nibabel as nib
import pathlib

def init_seedconnectivity_wf(seeds, 
        use_mov_pars, name = "firstlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file", "mask_file", "confounds_file"]), 
        name = "inputnode"
    )
    
    seednames = list(seeds.keys())
    seed_paths = [seeds[k] for k in seednames]
    
    meants = pe.MapNode(
        interface = fsl.ImageMeants(),
        name = "meants",
        iterfield = ["mask"]
    )
    meants.inputs.mask = seed_paths
        
    glm = pe.MapNode(
        interface = fsl.GLM(
            out_file = "beta.nii.gz",
            out_cope = "cope.nii.gz",
            out_varcb_name = "varcope.nii.gz",
            out_z_name = "zstat.nii.gz",
            demean = True
        ), 
        name = "glm",
        iterfield = ["design"]
    )
    
    gendoffile = pe.Node(
        interface = Dof(num_regressors = 1),
        name = "gendoffile"
    )

    splitcopes = pe.Node(
        interface = niu.Split(splits = [1 for seedname in seednames]),
        name = "splitcopes"
    )
    splitvarcopes = pe.Node(
        interface = niu.Split(splits = [1 for seedname in seednames]),
        name = "splitvarcopes"
    )
    splitzstats = pe.Node(
        interface = niu.Split(splits = [1 for seedname in seednames]),
        name = "splitzstats"
    )
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = sum([["%s_cope" % seedname, 
                "%s_varcope" % seedname, "%s_zstat" % seedname] 
            for seedname in seednames], []) + ["dof_file"]), 
        name = "outputnode"
    )
    
    workflow.connect([
        (inputnode, meants, [
            ("bold_file", "in_file")
        ]),
        (inputnode, glm, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (meants, glm, [
            ("out_file", "design")
        ]),
        
        (glm, splitcopes, [
            ("out_cope", "inlist"), 
        ]),
        (glm, splitvarcopes, [
            ("out_varcb", "inlist"), 
        ]),
        (glm, splitzstats, [
            ("out_z", "inlist"), 
        ]),
        
        (inputnode, gendoffile, [
            ("bold_file", "in_file"), 
        ]),
        (gendoffile, outputnode, [
            ("out_file", "dof_file"), 
        ]),
    ])
    
    for i, seedname in enumerate(seednames):
        workflow.connect(splitcopes, "out%i" % (i+1), outputnode, "%s_cope" % seedname)
        workflow.connect(splitvarcopes, "out%i" % (i+1), outputnode, "%s_varcope" % seedname)
        workflow.connect(splitzstats, "out%i" % (i+1), outputnode, "%s_zstat" % seedname)
    
    return workflow, seednames


def init_dualregression_wf(componentsfile, 
        use_mov_pars, name = "firstlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file", "mask_file", "confounds_file"]), 
        name = "inputnode"
    )
    
    ncomponents = nib.load(componentsfile).shape[3];
    fname, _ = _splitext(op.basename(componentsfile))
    componentnames = ["%s_%d" % (fname, i) for i in range(ncomponents)]
    
    glm0 = pe.Node(
        interface = fsl.GLM(
            out_file = "beta",
            demean = True
        ), 
        name = "glm0"
    )
    glm0.inputs.design = componentsfile
        
    glm1 = pe.Node(
        interface = fsl.GLM(
            out_file = "beta.nii.gz",
            out_cope = "cope.nii.gz",
            out_varcb_name = "varcope.nii.gz",
            out_z_name = "zstat.nii.gz",
            demean = True
        ), 
        name = "glm1"
    )
    
    splitcopesimage = pe.Node(
        interface = fsl.Split(dimension = "t"),
        name = "splitcopesimage"
    )
    splitvarcopesimage = pe.Node(
        interface = fsl.Split(dimension = "t"),
        name = "splitvarcopesimage"
    )
    splitzstatsimage = pe.Node(
        interface = fsl.Split(dimension = "t"),
        name = "splitzstatsimage"
    )
    
    gendoffile = pe.Node(
        interface = Dof(num_regressors = 1),
        name = "gendoffile"
    )
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = sum([["%s_cope" % componentname, 
                "%s_varcope" % componentname, "%s_zstat" % componentname] 
            for componentname in componentnames], []) + ["dof_file"]), 
        name = "outputnode"
    )

    splitcopes = pe.Node(
        interface = niu.Split(splits = [1 for componentname in componentnames]),
        name = "splitcopes"
    )
    splitvarcopes = pe.Node(
        interface = niu.Split(splits = [1 for componentname in componentnames]),
        name = "splitvarcopes"
    )
    splitzstats = pe.Node(
        interface = niu.Split(splits = [1 for componentname in componentnames]),
        name = "splitzstats"
    )
    
    workflow.connect([
        (inputnode, glm0, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (inputnode, glm1, [
            ("bold_file", "in_file"),
            ("mask_file", "mask")
        ]),
        (glm0, glm1, [
            ("out_file", "design")
        ]),
        
        (glm1, splitcopesimage, [
            ("out_cope", "in_file"), 
        ]),
        (glm1, splitvarcopesimage, [
            ("out_varcb", "in_file"), 
        ]),
        (glm1, splitzstatsimage, [
            ("out_z", "in_file"), 
        ]),
        (splitcopesimage, splitcopes, [
            ("out_files", "inlist"), 
        ]),
        (splitvarcopesimage, splitvarcopes, [
            ("out_files", "inlist"), 
        ]),
        (splitzstatsimage, splitzstats, [
            ("out_files", "inlist"), 
        ]),
        
        (inputnode, gendoffile, [
            ("bold_file", "in_file"), 
        ]),
        (gendoffile, outputnode, [
            ("out_file", "dof_file"), 
        ]),
    ])
    
    for i, componentname in enumerate(componentnames):
        workflow.connect(splitcopes, "out%i" % (i+1), outputnode, "%s_cope" % componentname)
        workflow.connect(splitvarcopes, "out%i" % (i+1), outputnode, "%s_varcope" % componentname)
        workflow.connect(splitzstats, "out%i" % (i+1), outputnode, "%s_zstat" % componentname)
    
    return workflow, componentnames

