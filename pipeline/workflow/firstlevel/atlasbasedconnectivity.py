# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from ...interface import ConnectivityMeasure, ResampleIfNeeded, MakeResultdicts

from ..memory import MemoryCalculator
from ...spec import Tags, Analysis, BandPassFilteredTag, ConfoundsRemovedTag
from ...utils import onlyboldentitiesdict


def init_atlasbasedconnectivity_wf(analysis, memcalc=MemoryCalculator()):
    """
    create workflow for brainatlas

    """
    assert isinstance(analysis, Analysis)
    assert isinstance(analysis.tags, Tags)

    # make bold file variant specification
    varianttupls = [("space", analysis.tags.space)]
    if analysis.tags.band_pass_filtered is not None:
        assert isinstance(analysis.tags.band_pass_filtered, BandPassFilteredTag)
        varianttupls.append(analysis.tags.band_pass_filtered.as_tupl())
    if analysis.tags.confounds_removed is not None:
        assert isinstance(analysis.tags.confounds_removed, ConfoundsRemovedTag)
        varianttupls.append(analysis.tags.confounds_removed.as_tupl())
    assert analysis.tags.smoothed is None

    boldfilevariant = (("bold_file",), tuple(varianttupls))

    assert analysis.name is not None
    workflow = pe.Workflow(name=analysis.name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "mask_file", "atlas_files", "metadata"]
        ),
        name="inputnode",
    )

    resampleifneeded = pe.MapNode(
        interface=ResampleIfNeeded(method="nearest"),
        name="connectivitymeasure",
        iterfield=["in_file"],
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "atlas_files", resampleifneeded, "in_file")
    workflow.connect(inputnode, "bold_file", resampleifneeded, "ref_file")

    connectivitymeasure = pe.MapNode(
        interface=ConnectivityMeasure(background_label=0, min_n_voxels=50),
        name="connectivitymeasure",
        iterfield=["atlas_file"],
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "bold_file", connectivitymeasure, "in_file")
    workflow.connect(inputnode, "mask_file", connectivitymeasure, "mask_file")
    workflow.connect(resampleifneeded, "out_file", connectivitymeasure, "atlas_file")

    connmatrixnames = ["time_series", "covariance", "correlation", "partial_correlation"]

    mergeconnmatrixresults = pe.Node(interface=niu.Merge(4), name="mergeconnmatrixresults")
    for i, outname in enumerate(connmatrixnames):
        workflow.connect(connectivitymeasure, outname, mergeconnmatrixresults, f"in{i+1}")

    outputnode = pe.Node(
        interface=MakeResultdicts(keys=["analysisname", "firstlevelname", "matrix"]),
        name="outputnode",
    )
    outputnode.inputs.analysisname = analysis.name
    outputnode.inputs.firstlevelname = connmatrixnames
    workflow.connect(
        [(inputnode, outputnode, [(("metadata", onlyboldentitiesdict), "basedict")])]
    )
    workflow.connect(mergeconnmatrixresults, "out", outputnode, "connectivity_matrix")

    return workflow, (boldfilevariant,)
