# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from ...interface import MakeResultdicts

from ..memory import MemoryCalculator
from ...spec import (
    Tags,
    Analysis,
    BandPassFilteredTag,
    ConfoundsRemovedTag,
    GrandMeanScaledTag,
    SmoothedTag,
)


def init_imageoutput_wf(analysis, memcalc=MemoryCalculator()):
    """
    create workflow for preprocessed image output

    """

    assert isinstance(analysis, Analysis)
    assert isinstance(analysis.tags, Tags)

    # make bold file variant specification
    varianttupls = [("space", analysis.tags.space)]
    confoundsfilefields = []
    if analysis.tags.grand_mean_scaled is not None:
        assert isinstance(analysis.tags.grand_mean_scaled, GrandMeanScaledTag)
        varianttupls.append(analysis.tags.grand_mean_scaled.as_tupl())
    if analysis.tags.band_pass_filtered is not None:
        assert isinstance(analysis.tags.band_pass_filtered, BandPassFilteredTag)
        varianttupls.append(analysis.tags.band_pass_filtered.as_tupl())
    if analysis.tags.confounds_removed is not None:
        assert isinstance(analysis.tags.confounds_removed, ConfoundsRemovedTag)
        varianttupls.append(analysis.tags.confounds_removed.as_tupl())
        confoundsfilefields.append("confounds_file")
        confoundsfilefields.append("confounds_file_with_header")
        varianttupls.append(("confounds_extract", (".+",)))  # always output all confounds
    if analysis.tags.smoothed is not None:
        assert isinstance(analysis.tags.smoothed, SmoothedTag)
        varianttupls.append(analysis.tags.smoothed.as_tupl())

    boldfilevariant = (("bold_file", *confoundsfilefields), tuple(varianttupls))

    assert analysis.name is not None
    workflow = pe.Workflow(name=analysis.name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=[
                "bold_file",
                "mask_file",
                "confounds_file_with_header",
                "confounds_file",
                "metadata",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        interface=MakeResultdicts(keys=["preproc", "confounds", "mask_file"]), name="outputnode",
    )
    workflow.connect(
        [
            (
                inputnode,
                outputnode,
                [
                    ("metadata", "basedict"),
                    ("bold_file", "preproc"),
                    ("mask_file", "mask_file"),
                    ("confounds_file_with_header", "confounds"),
                ],
            )
        ]
    )

    return workflow, (boldfilevariant,)
