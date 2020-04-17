# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ...interface import MergeColumnsTSV, ResampleIfNeeded, MakeResultdicts
from ...utils import ravel, onlyboldentitiesdict

from ..memory import MemoryCalculator
from ...spec import Tags, Analysis, BandPassFilteredTag, ConfoundsRemovedTag, SmoothedTag


def init_dualregression_wf(analysis, memcalc=MemoryCalculator()):
    """
    create a workflow to calculate dual regression for ICA seeds
    """
    assert isinstance(analysis, Analysis)
    assert isinstance(analysis.tags, Tags)

    # make bold file variant specification
    confoundsfilefields = []
    varianttupls = [("space", analysis.tags.space)]
    if analysis.tags.band_pass_filtered is not None:
        assert isinstance(analysis.tags.band_pass_filtered, BandPassFilteredTag)
        varianttupls.append(analysis.tags.band_pass_filtered.as_tupl())
    if analysis.tags.confounds_removed is not None:
        assert isinstance(analysis.tags.confounds_removed, ConfoundsRemovedTag)
        confounds_removed_names = tuple(
            name for name in analysis.tags.confounds_removed.names if "ica_aroma" in name
        )
        varianttupls.append(("confounds_removed", confounds_removed_names))
        confounds_extract_names = tuple(
            name for name in analysis.tags.confounds_removed.names if "ica_aroma" not in name
        )
        if len(confounds_extract_names) > 0:
            confoundsfilefields.append("confounds_file")
            varianttupls.append(("confounds_extract", confounds_extract_names))
    if analysis.tags.smoothed is not None:
        assert isinstance(analysis.tags.smoothed, SmoothedTag)
        varianttupls.append(analysis.tags.smoothed.as_tupl())

    boldfilevariant = (("bold_file", *confoundsfilefields), tuple(varianttupls))

    assert analysis.name is not None
    workflow = pe.Workflow(name=analysis.name)

    # input
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_file",
                *confoundsfilefields,
                "mask_file",
                "map_files",
                "map_components",
                "metadata",
            ]
        ),
        name="inputnode",
    )

    resampleifneeded = pe.MapNode(
        interface=ResampleIfNeeded(method="continuous"),
        name="connectivitymeasure",
        iterfield=["in_file"],
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "map_files", resampleifneeded, "in_file")
    workflow.connect(inputnode, "bold_file", resampleifneeded, "ref_file")

    # Delete zero voxels for mean time series
    applymask = pe.MapNode(
        interface=fsl.ApplyMask(),
        name="applymask",
        iterfield="in_file",
        mem_gb=memcalc.volume_std_gb,
    )
    workflow.connect(
        [
            (inputnode, applymask, [("mask_file", "mask_file")]),
            (resampleifneeded, applymask, [("out_file", "in_file")]),
        ]
    )

    # first step, calculate spatial regression of ICA components on to the
    # bold file
    glm0 = pe.MapNode(
        interface=fsl.GLM(out_file="beta", demean=True,),
        name="glm0",
        iterfield="design",
        mem_gb=memcalc.series_std_gb * 10,
    )
    workflow.connect(
        [
            (applymask, glm0, [("out_file", "design")]),
            (inputnode, glm0, [("bold_file", "in_file"), ("mask_file", "mask")]),
        ]
    )

    # second step, calculate the temporal regression of the time series
    # from the first step on to the bold file
    def make_contrastmat(map_file=None, confounds_file=None):
        """
        extract number of ICA components from 4d image and name them
        """
        import os
        from os import path as op

        from pipeline.utils import nvol, ncol
        import numpy as np

        ncomponents = nvol(map_file)
        if confounds_file is not None:
            nconfounds = ncol(confounds_file)
        else:
            nconfounds = 0
        contrastmat = np.zeros((ncomponents, ncomponents + nconfounds))
        contrastmat[:ncomponents, :ncomponents] = np.eye(ncomponents)

        out_file = op.join(os.getcwd(), "contrasts.tsv")
        np.savetxt(out_file, contrastmat, delimiter="\t")
        return out_file

    contrastmat = pe.MapNode(
        interface=niu.Function(
            input_names=["map_file", *confoundsfilefields],
            output_names=["out_file"],
            function=make_contrastmat,
        ),
        iterfield="map_file",
        name="contrastmat",
    )
    workflow.connect([(inputnode, contrastmat, [("map_files", "map_file")])])
    if confoundsfilefields:
        workflow.connect(
            [(inputnode, contrastmat, [(*confoundsfilefields, *confoundsfilefields)])]
        )

    glm1 = pe.MapNode(
        interface=fsl.GLM(
            out_file="beta.nii.gz",
            out_cope="cope.nii.gz",
            out_varcb_name="varcope.nii.gz",
            out_z_name="zstat.nii.gz",
            demean=True,
        ),
        name="glm1",
        iterfield=["design", "contrasts"],
        mem_gb=memcalc.series_std_gb * 10,
    )
    workflow.connect(
        [
            (inputnode, glm1, [("bold_file", "in_file"), ("mask_file", "mask")]),
            (contrastmat, glm1, [("out_file", "contrasts")]),
        ]
    )

    if confoundsfilefields:
        mergecolumns = pe.MapNode(
            interface=MergeColumnsTSV(2),
            name="mergecolumns",
            mem_gb=memcalc.min_gb,
            iterfield="in1",
            run_without_submitting=True,
        )
        workflow.connect(
            [
                (glm0, mergecolumns, [("out_file", "in1")]),
                (inputnode, mergecolumns, [(*confoundsfilefields, "in2")]),
                (mergecolumns, glm1, [("out_file", "design")]),
            ]
        )
    else:
        workflow.connect([(glm0, glm1, [("out_file", "design")])])

    # output

    outputnode = pe.Node(
        interface=MakeResultdicts(
            keys=["analysisname", "firstlevelname", "cope", "varcope", "zstat", "mask_file"]
        ),
        name="outputnode",
    )
    outputnode.inputs.analysisname = analysis.name
    workflow.connect(
        [
            (
                inputnode,
                outputnode,
                [
                    (("metadata", onlyboldentitiesdict), "basedict"),
                    ("mask_file", "mask_file"),
                    (("map_components", ravel), "firstlevelname"),
                ],
            ),
            (
                glm1,
                outputnode,
                [
                    (("out_cope", ravel), "cope"),
                    (("out_varcb", ravel), "varcope"),
                    (("out_z", ravel), "zstat"),
                ],
            ),
        ]
    )

    return workflow, (boldfilevariant,)
