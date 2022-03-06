# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
from nipype.pipeline import plugins as nip


def run_workflow(workflow: pe.Workflow):
    assert workflow.base_dir is not None

    workflow_args = dict(stop_on_first_crash=True, crashdump_dir=workflow.base_dir)
    workflow.config["execution"].update(workflow_args)

    graph = workflow.run()

    runner = nip.LinearPlugin(plugin_args=workflow_args)
    runner.run(graph, updatehash=False, config=workflow.config)

    return graph
