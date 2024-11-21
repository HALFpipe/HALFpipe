# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import fsl
from niworkflows.interfaces.utility import KeySelect

from ...interfaces.utility.remove_volumes import RemoveVolumes
from ..constants import Constants
from ..memory import MemoryCalculator


def init_fmriprep_adapter_wf(
    name: str = "fmriprep_adapter_wf",
    memcalc: MemoryCalculator | None = None,
):
    """
    Fmriprep resamples all data to atlas space, but we need the data in a different format.
    Specifically, we dont want that data outside of the brain and we dont want the dummy scans.
    This workflow takes care of that
    """

    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_file",  # "bold_std",
                "target_mask",  # "bold_mask_std",
                # "spatial_reference", # not used anymore
                "resampling_reference",
                "skip_vols",
                "confounds",
                "vals",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "vals"]),
        name="outputnode",
    )

    # KeySelect(fields=["bold_std", "bold_std_ref", "bold_mask_std", "std_dseg"]),
    # Ke#ySelect(fields=["bold_file", "bold_ref_file", "target_mask", "std_dseg"]),

    #
    select_std = pe.Node(
        KeySelect(fields=["bold_file", "target_mask"]),
        name="select_std",
        run_without_submitting=True,
        nohash=True,
    )
    select_std.inputs.key = f"{Constants.reference_space}_res-{Constants.reference_res}"
    #

    workflow.connect(inputnode, "bold_file", select_std, "bold_file")
    workflow.connect(inputnode, "target_mask", select_std, "target_mask")
    workflow.connect(inputnode, "resampling_reference", select_std, "keys")

    # We apply mask to remove voxels that are outside brain
    apply_mask = pe.Node(
        interface=fsl.ApplyMask(),
        name="apply_mask",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(select_std, "bold_file", apply_mask, "in_file")
    workflow.connect(select_std, "target_mask", apply_mask, "mask_file")

    # Take multiple inputs and put them on a list (through Merge node),
    # so we can apply the skip_vols node to both the bold file and the confounds
    merge = pe.Node(niu.Merge(2), name="merge")
    workflow.connect(apply_mask, "out_file", merge, "in1")
    workflow.connect(inputnode, "confounds", merge, "in2")

    # Fmriprep does not actually get rid of volumes we want skipped (in "skip_vols")
    # so we do it ourselves
    skip_vols = pe.MapNode(
        RemoveVolumes(),
        iterfield="in_file",
        name="skip_vols",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(merge, "out", skip_vols, "in_file")
    workflow.connect(inputnode, "skip_vols", skip_vols, "skip_vols")
    workflow.connect(select_std, "target_mask", skip_vols, "mask")

    #
    workflow.connect(skip_vols, "out_file", outputnode, "files")
    workflow.connect(select_std, "target_mask", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    return workflow


# vals: QC metrics, metadata, scanner metadata
