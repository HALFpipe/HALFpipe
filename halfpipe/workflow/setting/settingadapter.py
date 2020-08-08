# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu

from ...interface import Select, Exec


def add_setting_adapter(workflow):
    inputnode = workflow.get_node("inputnode")

    #
    select = pe.Node(Select(regex=r".+\.tsv"), name="select", run_without_submitting=True)
    workflow.connect(inputnode, "files", select, "in_list")

    #
    adapter = pe.Node(
        Exec(fieldtpls=[("bold", "firststr"), ("confounds", "firststr")]),
        name="adapter",
        run_without_submitting=True,
    )  # discard any extra files, keep only first match
    workflow.connect(select, "match_list", adapter, "confounds")
    workflow.connect(select, "other_list", adapter, "bold")

    return adapter


def init_setting_adapter_wf(suffix=None):
    name = f"setting_adapter_wf"
    if suffix is not None:
        name = f"{name}_{suffix}"
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=["files", "mask", "vals"]), name="inputnode",)
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["bold", "confounds", "mask", "vals"]), name="outputnode",
    )
    workflow.connect(inputnode, "mask", outputnode, "mask")
    workflow.connect(inputnode, "vals", outputnode, "vals")

    adapter = add_setting_adapter(workflow)
    workflow.connect(adapter, "bold", outputnode, "bold")
    workflow.connect(adapter, "confounds", outputnode, "confounds")

    return workflow
