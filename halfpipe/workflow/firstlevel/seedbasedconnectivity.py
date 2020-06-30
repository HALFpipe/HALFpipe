# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ...interface import MergeColumnsTSV, ResampleIfNeeded, MakeResultdicts, MakeDofVolume
from ...utils import ravel

from ..memory import MemoryCalculator
from ...spec import (
    Tags,
    Analysis,
    BandPassFilteredTag,
    ConfoundsRemovedTag,
    SmoothedTag,
    GrandMeanScaledTag,
)


def init_seedbasedconnectivity_wf(analysis, memcalc=MemoryCalculator()):
    """
    create workflow to calculate seed connectivity maps
    """
    assert isinstance(analysis, Analysis)
    assert isinstance(analysis.tags, Tags)

    # make bold file variant specification
    confoundsfilefields = []
    varianttupls = [("space", analysis.tags.space)]
    if analysis.tags.grand_mean_scaled is not None:
        assert isinstance(analysis.tags.grand_mean_scaled, GrandMeanScaledTag)
        varianttupls.append(analysis.tags.grand_mean_scaled.as_tupl())
    if analysis.tags.band_pass_filtered is not None:
        assert isinstance(analysis.tags.band_pass_filtered, BandPassFilteredTag)
        varianttupls.append(analysis.tags.band_pass_filtered.as_tupl())
    if analysis.tags.confounds_removed is not None:
        assert isinstance(analysis.tags.confounds_removed, ConfoundsRemovedTag)
        confounds_removed_names = tuple(
            name for name in analysis.tags.confounds_removed.names if "aroma_motion" in name
        )
        varianttupls.append(("confounds_removed", confounds_removed_names))
        confounds_extract_names = tuple(
            name for name in analysis.tags.confounds_removed.names if "aroma_motion" not in name
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
                "seed_files",
                "seed_names",
                "metadata",
            ]
        ),
        name="inputnode",
    )

    resampleifneeded = pe.MapNode(
        interface=ResampleIfNeeded(method="nearest"),
        name="resampleifneeded",
        iterfield=["in_file"],
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "seed_files", resampleifneeded, "in_file")
    workflow.connect(inputnode, "bold_file", resampleifneeded, "ref_file")

    # Delete zero voxels for the seeds
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

    # calculate the mean time series of the region defined by each mask
    meants = pe.MapNode(
        interface=fsl.ImageMeants(), name="meants", iterfield="mask", mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(
        [
            (inputnode, meants, [("bold_file", "in_file")]),
            (applymask, meants, [("out_file", "mask")]),
        ]
    )

    def make_contrastmat(confounds_file=None):
        import os
        from os import path as op

        from halfpipe.utils import ncol
        import numpy as np

        if confounds_file is not None:
            nconfounds = ncol(confounds_file)
        else:
            nconfounds = 0
        contrastmat = np.zeros((1, 1 + nconfounds))
        contrastmat[0, 0] = 1

        out_file = op.join(os.getcwd(), "contrasts.tsv")
        np.savetxt(out_file, contrastmat, delimiter="\t")
        return out_file

    contrastmat = pe.Node(
        interface=niu.Function(
            input_names=[*confoundsfilefields],
            output_names=["out_file"],
            function=make_contrastmat,
        ),
        name="contrastmat",
    )
    if confoundsfilefields:
        workflow.connect([(inputnode, contrastmat, [(*confoundsfilefields, *confoundsfilefields)])])

    designnode = pe.Node(niu.IdentityInterface(fields=["design"]), name="designnode")
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
                (meants, mergecolumns, [("out_file", "in1")]),
                (inputnode, mergecolumns, [(*confoundsfilefields, "in2")]),
                (mergecolumns, designnode, [("out_file", "design")]),
            ]
        )
    else:
        workflow.connect([(meants, designnode, [("out_file", "design")])])

    # calculate the regression of the mean time series
    # onto the functional image.
    # the result is the seed connectivity map
    glm = pe.MapNode(
        interface=fsl.GLM(
            out_file="beta.nii.gz",
            out_cope="cope.nii.gz",
            out_varcb_name="varcope.nii.gz",
            out_z_name="zstat.nii.gz",
            demean=True,
        ),
        name="glm",
        iterfield="design",
        mem_gb=memcalc.series_std_gb * 5,
    )
    workflow.connect(
        [
            (inputnode, glm, [("bold_file", "in_file")]),
            (contrastmat, glm, [("out_file", "contrasts")]),
            (designnode, glm, [("design", "design")]),
        ]
    )

    # make dof volume
    makedofvolume = pe.MapNode(
        interface=MakeDofVolume(), iterfield=["design"], name="makedofvolume",
    )
    workflow.connect(
        [
            (inputnode, makedofvolume, [("bold_file", "bold_file")]),
            (designnode, makedofvolume, [("design", "design")]),
        ]
    )

    outputnode = pe.Node(
        interface=MakeResultdicts(
            keys=[
                "firstlevelanalysisname",
                "firstlevelfeaturename",
                "cope",
                "varcope",
                "zstat",
                "dof_file",
                "mask_file",
            ]
        ),
        name="outputnode",
    )
    outputnode.inputs.firstlevelanalysisname = analysis.name
    workflow.connect(
        [
            (
                inputnode,
                outputnode,
                [
                    ("metadata", "basedict"),
                    ("mask_file", "mask_file"),
                    ("seed_names", "firstlevelfeaturename"),
                ],
            ),
            (makedofvolume, outputnode, [("out_file", "dof_file")]),
            (
                glm,
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
