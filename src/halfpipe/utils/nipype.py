# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe

from ..plugins import SimplePlugin


def run_workflow(workflow: pe.Workflow):
    """
    Runs a Nipype workflow serially.

    Args:
        workflow (nipype.pipeline.engine.Workflow): The Nipype workflow to run.

    Returns:
        graph: The graph of the executed workflow.
    """
    if workflow.base_dir is None:
        raise ValueError("Workflow must have a base directory")

    workflow_args = dict(stop_on_first_crash=True, crashdump_dir=workflow.base_dir)
    workflow.config["execution"].update(workflow_args)

    runner = SimplePlugin(plugin_args=workflow_args)
    graph = workflow.run(plugin=runner)

    return graph
