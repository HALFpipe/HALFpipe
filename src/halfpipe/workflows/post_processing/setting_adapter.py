# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu

from ...interfaces.utility.file_type import SplitByFileType
from ...utils.ops import first_str


def add_setting_adapter(workflow):
    inputnode = workflow.get_node("inputnode")

    #
    split_by_file_type = pe.Node(SplitByFileType(), name="split_by_file_type")
    workflow.connect(inputnode, "files", split_by_file_type, "files")

    # discard any extra files, keep only first match
    bold_adapter = pe.Node(
        niu.Function(input_names=["obj"], output_names=["bold"], function=first_str),
        name="bold_adapter",
    )
    tsv_adapter = pe.Node(
        niu.Function(input_names=["obj"], output_names=["confounds"], function=first_str),
        name="tsv_adapter",
    )
    workflow.connect(split_by_file_type, "nifti_files", bold_adapter, "obj")
    workflow.connect(split_by_file_type, "tsv_files", tsv_adapter, "obj")

    return bold_adapter, tsv_adapter


def init_setting_adapter_wf(suffix: str | None = None):
    name = "setting_adapter_wf"
    if suffix is not None:
        name = f"{name}_{suffix}"
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["files", "mask", "vals"]),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["bold", "confounds", "mask", "vals"]),
        name="outputnode",
    )
    workflow.connect(inputnode, "mask", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    bold_adapter, tsv_adapter = add_setting_adapter(workflow)
    workflow.connect(bold_adapter, "bold", outputnode, "bold")
    workflow.connect(tsv_adapter, "confounds", outputnode, "confounds")

    return workflow
