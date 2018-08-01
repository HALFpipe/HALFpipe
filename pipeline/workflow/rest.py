# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

def init_seed_connectivity_wf(seeds, name = "firstlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file", "mask_file"]), 
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
        (glm, outputnode, [
            ("out_cope", "copes"), 
            ("out_varcb", "varcopes"),
            ("out_z", "zstats")
        ]),
    ])
    
    return workflow, seed_names
